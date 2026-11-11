"""唯讀蝦皮試算 CLI。"""
import argparse
import csv
import hashlib
import json
import sys
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, ROUND_CEILING
from pathlib import Path


HEADERS = {
    'orders': 'order_id track round sku is_stranger accepted_on status completed_on bank_settled_on refund_settled_on price shipping cost_id estimated_cost actual_cost return_loss defect purchased disposed realized_loss cancel_reason'.split(),
    'cashflow': 'date track sku category direction estimated_twd actual_twd uses_reserve cost_id order_id'.split(),
    'daily': 'date track round sku change impressions clicks ctr ad_spend orders received_amount in_transit notes'.split(),
}


class Inputs:
    def __init__(self):
        self.errors = []

    def error(self, file, row, column, message):
        self.errors.append(dict(file=str(file), row=row, column=column, message=message))

    def load_json(self, path):
        try:
            value = json.loads(Path(path).read_text(encoding='utf-8-sig'))
            if not isinstance(value, dict):
                raise ValueError('最外層須為物件')
            return value
        except (OSError, ValueError, UnicodeError) as exc:
            self.error(path, None, None, f'無法讀取 JSON：{exc}')
            return {}

    def number(self, value, file, row, column, *, maximum=None, integer=False):
        try:
            n = dec(value)
            if isinstance(value, bool) or not n.is_finite() or n < 0 or (maximum is not None and n > maximum) or (integer and n != n.to_integral_value()):
                raise ValueError()
            return n
        except (InvalidOperation, ValueError):
            self.error(file, row, column, '須為範圍內的有限非負數' + ('整數' if integer else ''))
            return None

    def day(self, value, file, row, column):
        try:
            if not isinstance(value, str) or len(value) != 10:
                raise ValueError()
            return date.fromisoformat(value)
        except (ValueError, TypeError):
            self.error(file, row, column, '須為 YYYY-MM-DD 日期')
            return None

    def csv(self, path, kind):
        if not path:
            return []
        try:
            with open(path, encoding='utf-8-sig', newline='') as stream:
                reader = csv.DictReader(stream, strict=True)
                fields = reader.fieldnames or []
                for column in HEADERS[kind]:
                    if column not in fields:
                        self.error(path, 0, column, '缺少必要欄位')
                if len(fields) != len(set(fields)):
                    self.error(path, 0, None, '重複欄位')
                rows = list(reader)
            for i, row in enumerate(rows, 1):
                if None in row or any(v is None for v in row.values()):
                    self.error(path, i, None, '資料欄數與標頭不符')
            return rows
        except (OSError, UnicodeError, csv.Error) as exc:
            self.error(path, None, None, f'無法讀取 CSV：{exc}')
            return []

    def params(self, p, file):
        for key in ('plan', 'category', 'return_rate', 'per_return_loss', 'fx', 'wholesale_discount', 'auto_ad', 'inventory', 'tracks', 'skus'):
            if key not in p:
                self.error(file, None, key, '缺少必要參數')
        if p.get('plan') not in (1, 2) or isinstance(p.get('plan'), bool):
            self.error(file, None, 'plan', '方案須為 1 或 2')
        if not isinstance(p.get('category'), str) or not p.get('category'):
            self.error(file, None, 'category', '須為費率類目名稱')
        for key in ('return_rate', 'per_return_loss', 'fx', 'wholesale_discount'):
            self.number(p.get(key), file, None, key, maximum=1 if key in ('return_rate', 'wholesale_discount') else None)
        if not isinstance(p.get('auto_ad'), bool):
            self.error(file, None, 'auto_ad', '須為布林值')
        tracks = p.get('tracks')
        if not isinstance(tracks, dict) or not tracks:
            self.error(file, None, 'tracks', '須提供軌道設定')
            tracks = {}
        for track, config in tracks.items():
            if track not in ('A', 'B') or not isinstance(config, dict):
                self.error(file, None, 'tracks', '軌道僅限 A 或 B，設定須為物件')
                continue
            for key in ('budget', 'reserve_requirement') + (('in_transit_cap',) if track == 'B' else ()):
                self.number(config.get(key), file, None, f'tracks.{track}.{key}')
            if isinstance(config.get('budget'), (int, float)) and isinstance(config.get('reserve_requirement'), (int, float)) and config['reserve_requirement'] > config['budget']:
                self.error(file, None, f'tracks.{track}.reserve_requirement', '準備金不得超過預算')
            rounds = config.get('rounds')
            if not isinstance(rounds, dict) or not rounds or not isinstance(config.get('current_round'), str) or config['current_round'] not in rounds:
                self.error(file, None, f'tracks.{track}.rounds', '須提供各輪起日及有效 current_round')
                continue
            starts = []
            for name, start in rounds.items():
                d = self.day(start, file, None, f'tracks.{track}.rounds.{name}')
                if d:
                    starts.append(d)
            starts.sort()
            if any((b - a).days < 14 for a, b in zip(starts, starts[1:])):
                self.error(file, None, f'tracks.{track}.rounds', '接單期不得重疊')
        skus = p.get('skus')
        if not isinstance(skus, list) or not skus:
            self.error(file, None, 'skus', '須提供非空 SKU 陣列')
            skus = []
        seen = set()
        for i, s in enumerate(skus):
            prefix = f'skus.{i}.'
            if not isinstance(s, dict):
                self.error(file, None, prefix, '須為物件')
                continue
            if not isinstance(s.get('sku'), str) or not s.get('sku') or s.get('sku') in seen:
                self.error(file, None, prefix + 'sku', 'SKU 須為唯一非空字串')
            else:
                seen.add(s['sku'])
            if not isinstance(s.get('track'), str) or s['track'] not in tracks:
                self.error(file, None, prefix + 'track', '未知軌道')
            for key in ('price', 'shipping', 'promotion', 'gift', 'packaging', 'preorder_fee', 'tuning_rounds') + (('landed_cost', 'conversion_rate') if s.get('track') == 'A' else ()):
                self.number(s.get(key), file, None, prefix + key, maximum=1 if key == 'conversion_rate' else None, integer=key == 'tuning_rounds')
            if s.get('track') == 'B':
                items = s.get('items')
                if not isinstance(items, list) or not items:
                    self.error(file, None, prefix + 'items', '須提供到手成本品項')
                    continue
                for j, item in enumerate(items):
                    if not isinstance(item, dict):
                        self.error(file, None, prefix + f'items.{j}', '須為物件')
                        continue
                    for key in ('retail_jpy', 'domestic_shipping_jpy', 'international_shipping', 'import_tax', 'units'):
                        self.number(item.get(key), file, None, prefix + f'items.{j}.{key}', integer=key == 'units')
        inventory = p.get('inventory')
        if not isinstance(inventory, list):
            self.error(file, None, 'inventory', '須為陣列')
            return
        for i, inv in enumerate(inventory):
            prefix = f'inventory.{i}.'
            if not isinstance(inv, dict):
                self.error(file, None, prefix, '須為物件')
                continue
            if not isinstance(inv.get('sku'), str) or inv['sku'] not in seen or not isinstance(inv.get('track'), str) or inv['track'] not in tracks:
                self.error(file, None, prefix + 'sku', '未知 SKU 或軌道')
            for key in ('units', 'book_cost_per_unit', 'est_net_recovery_per_unit'):
                self.number(inv.get(key), file, None, prefix + key, integer=key == 'units')
            if not isinstance(inv.get('irrevocable'), bool):
                self.error(file, None, prefix + 'irrevocable', '須為布林值')

    def rates(self, rates, p, file, as_of):
        needed = ('payment', 'plan1', 'plan2_low', 'plan2_fixed', 'plan2_boundary', 'min_product_ad_bid', 'overseas_card', 'category_' + str(p.get('category')))
        for name in sorted(set(needed) | set(rates)):
            rate = rates.get(name)
            if not isinstance(rate, dict):
                self.error(file, None, name, '缺少必要費率物件')
                continue
            self.number(rate.get('value'), file, None, name + '.value', maximum=1 if name in ('payment', 'plan1', 'plan2_low', 'overseas_card') or name.startswith('category_') else None)
            for key in ('effective_from', 'checked_on'):
                d = self.day(rate.get(key), file, None, name + '.' + key)
                if key == 'effective_from' and d and as_of and d > as_of:
                    self.error(file, None, name + '.' + key, '判讀日早於費率生效日')
        for plan in ('plan1', 'plan2_low'):
            try:
                if sum(dec(rates[k]['value']) for k in ('payment', 'category_' + str(p.get('category')), plan)) >= 1:
                    self.error(file, None, plan, '百分比費率合計須小於 1')
            except (KeyError, TypeError, InvalidOperation):
                pass

    def rows(self, kind, rows, path, p, as_of):
        sku_map = {s['sku']: s for s in p['skus']}
        ids = set()
        for i, o in enumerate(rows, 1):
            if any(k not in o for k in HEADERS[kind]) or None in o or any(v is None for v in o.values()):
                continue
            track = o['track']
            if track not in p['tracks']:
                self.error(path, i, 'track', '未知軌道')
                continue
            if (kind != 'cashflow' or o['sku']) and (o['sku'] not in sku_map or sku_map[o['sku']]['track'] != track):
                self.error(path, i, 'sku', 'SKU 與軌道不符')
            numeric = {'orders': ('price', 'shipping', 'estimated_cost', 'actual_cost', 'return_loss', 'realized_loss'),
                       'cashflow': ('estimated_twd', 'actual_twd'),
                       'daily': ('impressions', 'clicks', 'ctr', 'ad_spend', 'orders', 'received_amount', 'in_transit')}[kind]
            for k in numeric:
                if k in ('actual_cost', 'actual_twd') and o[k] == '':
                    continue
                self.number(o[k], path, i, k, maximum=1 if k == 'ctr' else None, integer=k in ('impressions', 'clicks', 'orders'))
            dates = {'orders': ('accepted_on', 'completed_on', 'bank_settled_on', 'refund_settled_on'), 'cashflow': ('date',), 'daily': ('date',)}[kind]
            parsed = {}
            for k in dates:
                if o[k] == '' and k not in ('accepted_on', 'date'):
                    continue
                parsed[k] = self.day(o[k], path, i, k)
                if parsed[k] and as_of and parsed[k] > as_of:
                    self.error(path, i, k, '日期晚於判讀日')
            bools = ('is_stranger', 'defect', 'purchased', 'disposed') if kind == 'orders' else (('uses_reserve',) if kind == 'cashflow' else ())
            for k in bools:
                if o[k] not in ('true', 'false'):
                    self.error(path, i, k, '須為 true 或 false')
            if kind == 'orders':
                for k in ('order_id', 'cost_id'):
                    if not o[k]:
                        self.error(path, i, k, '不得留白')
                if o['order_id'] in ids:
                    self.error(path, i, 'order_id', '重複訂單 ID')
                ids.add(o['order_id'])
                if o['status'] not in ('accepted', 'purchased', 'shipped', 'kept', 'returned', 'cancelled'):
                    self.error(path, i, 'status', '未知訂單狀態')
                if o['status'] == 'cancelled' and o['cancel_reason'] not in ('buyer', 'supplier', 'other'):
                    self.error(path, i, 'cancel_reason', '取消單須提供 buyer、supplier 或 other')
                if o['purchased'] == 'true' and o['actual_cost'] == '':
                    self.error(path, i, 'actual_cost', '已採購須提供實際成本')
                accepted = parsed.get('accepted_on')
                for k, d in parsed.items():
                    if d and accepted and d < accepted:
                        self.error(path, i, k, '不得早於接單日')
                config = p['tracks'][track]
                start = config['rounds'].get(o['round'])
                if not start or (accepted and not 0 <= (accepted - date.fromisoformat(start)).days < 14):
                    self.error(path, i, 'round', '接單日與所屬輪次 Day 1–14 不符')
            elif kind == 'cashflow':
                if o['direction'] not in ('in', 'out'):
                    self.error(path, i, 'direction', '須為 in 或 out')
                if o['category'] not in ('procurement', 'ad', 'sample', 'packaging', 'refund', 'bank_receipt', 'reserve_topup', 'loss', 'other'):
                    self.error(path, i, 'category', '未知收支類別')
                if o['category'] == 'reserve_topup' and o['direction'] != 'in':
                    self.error(path, i, 'direction', '準備金補回須為流入')
                if o['uses_reserve'] == 'true' and (o['direction'] != 'out' or o['category'] not in ('refund', 'loss')):
                    self.error(path, i, 'uses_reserve', '準備金僅支應退款、退貨運費與瑕疵損失')
            else:
                config = p['tracks'][track]
                start = config['rounds'].get(o['round'])
                if not start or (parsed.get('date') and o['date'] < start):
                    self.error(path, i, 'round', '每日資料須有有效輪次，且不得早於輪次起日')


def dec(value):
    return Decimal(str(value))


def money(value):
    return float(dec(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def fees(p, rates, price, shipping):
    transaction = price * dec(rates['category_' + p['category']]['value'])
    payment = (price + shipping) * dec(rates['payment']['value'])
    if p['plan'] == 1:
        program = price * dec(rates['plan1']['value'])
    elif price < dec(rates['plan2_boundary']['value']):
        program = price * dec(rates['plan2_low']['value'])
    else:
        program = dec(rates['plan2_fixed']['value'])
    return transaction, payment, program


def economics(p, rates):
    result = {}
    for s in p['skus']:
        price, shipping = dec(s['price']), dec(s['shipping'])
        cost = dec(s['landed_cost']) if s['track'] == 'A' else Decimal(0)
        item_costs = []
        if s['track'] == 'B':
            for item in s['items']:
                unit = ((dec(item['retail_jpy']) * dec(p['wholesale_discount']) + dec(item['domestic_shipping_jpy'])) * dec(p['fx']) * (1 + dec(rates['overseas_card']['value'])) + dec(item['international_shipping']) + dec(item['import_tax']))
                item_costs.append(dict(unit_cost=money(unit), units=item['units']))
                cost += unit * dec(item['units'])
        transaction, payment, program = fees(p, rates, price, shipping)
        fixed = sum(dec(s[k]) for k in ('promotion', 'gift', 'packaging', 'preorder_fee'))
        kept = price - cost - fixed - transaction - payment - program
        expected = (1 - dec(p['return_rate'])) * kept - dec(p['return_rate']) * dec(p['per_return_loss'])
        result[s['sku']] = dict(kept_order_profit=money(kept), expected_profit=money(expected),
                                program_fee=money(program), payment_fee=money(payment),
                                order_cost=money(cost), item_costs=item_costs,
                                cpa_cap=money(expected * (Decimal('0.5') if s['track'] == 'B' else 1)),
                                break_even_cpc=money(expected * dec(s['conversion_rate'])) if s['track'] == 'A' else None,
                                flags=[])
        if expected < (50 if s['track'] == 'A' else 60):
            result[s['sku']]['flags'].append('不碰' if s['track'] == 'A' else '不准上架')
        if s['track'] == 'A' and expected * dec(s['conversion_rate']) < dec(rates['min_product_ad_bid']['value']):
            result[s['sku']]['flags'].append('不可依賴付費廣告')
        other = dec(rates['category_' + p['category']]['value']) + dec(rates['payment']['value'])
        bands = [('plan1', dec(rates['plan1']['value']), Decimal(0))] if p['plan'] == 1 else [
            ('plan2_low', dec(rates['plan2_low']['value']), Decimal(0)),
            ('plan2_fixed', Decimal(0), dec(rates['plan2_fixed']['value']))]
        candidates = []
        for band, percent, fee in bands:
            candidate = ((cost + fixed + fee + shipping * dec(rates['payment']['value'])) / (1 - other - percent)).quantize(Decimal('0.01'), rounding=ROUND_CEILING)
            boundary = dec(rates['plan2_boundary']['value'])
            if band == 'plan2_low' and not 1 <= candidate < boundary:
                continue
            if band == 'plan2_fixed' and candidate < boundary:
                continue
            candidates.append(dict(price=money(candidate), band=band))
        chosen = min(candidates, key=lambda c: c['price']) if candidates else dict(price=None, band=None)
        result[s['sku']]['liquidation'] = dict(**chosen, candidates=candidates)
    return result


def mature(o, as_of):
    if o['status'] in ('cancelled', 'returned'):
        return bool(o['refund_settled_on'])
    return bool(o['bank_settled_on'] and o['completed_on'] and
                (as_of - date.fromisoformat(o['completed_on'])).days >= 7)


def metrics(rows, as_of):
    strangers = [o for o in rows if o['is_stranger'] == 'true']
    matured = [o for o in strangers if mature(o, as_of)]
    n = len(matured)
    defects = sum(o['defect'] == 'true' for o in matured)
    immediate = [o for o in strangers if o['track'] == 'B' and o['defect'] == 'true' and o not in matured]
    attempts = sum(o['purchased'] == 'true' or (o['status'] == 'cancelled' and o['cancel_reason'] == 'supplier') for o in strangers)
    supplier_failures = sum(o['status'] == 'cancelled' and o['cancel_reason'] == 'supplier' for o in strangers)
    return dict(accepted=len(strangers), matured=n,
                completed=sum(o['status'] == 'kept' for o in matured),
                cancelled=sum(o['status'] == 'cancelled' for o in strangers),
                cancel_rate=sum(o['status'] == 'cancelled' for o in strangers) / len(strangers) if strangers else None,
                cancel_rate_status='OK' if strangers else 'PENDING',
                supplier_fulfillment_rate=(attempts - supplier_failures) / attempts if attempts else None,
                supplier_fulfillment_rate_status='OK' if attempts else 'PENDING',
                defect_rate=(defects + len(immediate)) / (n + len(immediate)) if n + len(immediate) else None,
                defect_rate_status='OK' if n + len(immediate) else 'PENDING',
                return_rate=sum(o['status'] == 'returned' for o in matured) / n if n else None,
                return_rate_status='OK' if n else 'PENDING')


def amount(row):
    return dec(row['actual_twd'] if row['actual_twd'] != '' else row['estimated_twd'])


def realized_loss(rows, flows):
    return sum(dec(o['realized_loss']) + dec(o['return_loss']) for o in rows if o['is_stranger'] == 'true') + sum(amount(f) for f in flows if f['direction'] == 'out' and f['category'] in ('sample', 'ad', 'loss'))


def inventory_loss(inventory):
    return sum(max(0, dec(i['units']) * (dec(i['book_cost_per_unit']) - dec(i['est_net_recovery_per_unit']))) for i in inventory)


def actual_profit(p, rates, rows, as_of):
    sku_map = {s['sku']: s for s in p['skus']}
    return sum(dec(o['price']) - dec(o['actual_cost']) - sum(fees(p, rates, dec(o['price']), dec(o['shipping']))) - sum(dec(sku_map[o['sku']][k]) for k in ('promotion', 'gift', 'packaging', 'preorder_fee')) for o in rows if o['is_stranger'] == 'true' and o['status'] == 'kept' and mature(o, as_of))


def ledger(p, orders, flows, as_of):
    states = {}
    for track, config in p['tracks'].items():
        rows = [o for o in orders if o['track'] == track and o['round'] == config['current_round']]
        tf = [f for f in flows if f['track'] == track]
        requirement = dec(config['reserve_requirement'])
        balance = requirement - sum(amount(f) for f in tf if f['uses_reserve'] == 'true' and f['direction'] == 'out')
        balance += sum(amount(f) for f in tf if f['category'] == 'reserve_topup')
        states[track] = dict(metrics=metrics(rows, as_of), reserve_balance=money(balance), reserve_gap=money(max(0, requirement - balance)))
        outflows = sum(amount(f) for f in tf if f['direction'] == 'out')
        inflows = sum(amount(f) for f in tf if f['direction'] == 'in')
        costs = {}
        for o in orders:
            if o['track'] == track and not (o['status'] == 'cancelled' and o['purchased'] == 'false'):
                costs[o['cost_id']] = dec(o['actual_cost'] or o['estimated_cost'])
        unpaid = Decimal(0)
        for cost_id, cost in costs.items():
            paid = sum(amount(f) for f in tf if f['category'] == 'procurement' and f['cost_id'] == cost_id and f['direction'] == 'out')
            unpaid += max(0, cost - paid)
        inventory = [i for i in p['inventory'] if i['track'] == track]
        for inv in inventory:
            if inv['irrevocable'] and inv.get('cost_id') not in costs:
                paid = sum(amount(f) for f in tf if inv.get('cost_id') and f['cost_id'] == inv['cost_id'] and f['category'] == 'procurement' and f['direction'] == 'out')
                unpaid += max(0, dec(inv['units']) * dec(inv['book_cost_per_unit']) - paid)
        realized = realized_loss([o for o in orders if o['track'] == track], tf)
        unrecoverable = inventory_loss(inventory)
        states[track].update(realized_loss=money(realized), unrecoverable_inventory=money(unrecoverable), actual_loss=money(realized + unrecoverable))
        states[track].update(available_cash=money(dec(config['budget']) + inflows - outflows),
                             paid_spend=money(outflows), unpaid_obligations=money(unpaid),
                             exposure=money(outflows + unpaid), exposure_limit=money(dec(config['budget']) - requirement))
        if track == 'B':
            latest = {}
            for o in sorted((o for o in orders if o['track'] == track), key=lambda o: (o['accepted_on'], o['order_id'])):
                latest[o['cost_id']] = o
            occupied = Decimal(0)
            for o in latest.values():
                if o['disposed'] == 'true' or (o['status'] == 'cancelled' and o['purchased'] == 'false'):
                    continue
                if o['status'] == 'kept' and o['bank_settled_on']:
                    continue
                occupied += dec(o['actual_cost'] if o['purchased'] == 'true' else o['estimated_cost'])
            cap = dec(config['in_transit_cap'])
            states[track]['in_transit'] = dict(occupied=money(occupied), remaining=money(cap - occupied), cap=money(cap))
    return states


def verdict(p, rates, orders, flows, days, states, as_of):
    actions = []
    state = 'NORMAL'
    pending = False

    def action(scope, rule, instruction, evidence):
        actions.append(dict(scope=scope, rule=rule, instruction=instruction, evidence=evidence))

    for track, config in p['tracks'].items():
        rows = [o for o in orders if o['track'] == track and o['round'] == config['current_round']]
        m = states[track]['metrics']
        ad = sum(dec(d['ad_spend']) for d in days if d['track'] == track and d['round'] == config['current_round'])
        avg = (actual_profit(p, rates, rows, as_of) - ad) / m['completed'] if m['completed'] else None
        m['avg_contribution_after_ads'] = money(avg) if avg is not None else None
        m['avg_contribution_after_ads_status'] = 'OK' if avg is not None else 'PENDING'
        day = (as_of - date.fromisoformat(config['rounds'][config['current_round']])).days + 1
        if states[track]['reserve_gap'] > 0:
            if state == 'NORMAL':
                state = 'PAUSED'
            action('project', 'RESERVE-PAUSE', '暫停新的廣告與需採購的新承諾；只履行暫停前已接訂單，補足準備金後再評估', dict(track=track, balance=states[track]['reserve_balance'], gap=states[track]['reserve_gap']))
        low_reserve = track == 'B' and dec(states[track]['reserve_balance']) < dec(config['reserve_requirement']) / 2
        if low_reserve:
            state = 'STOP_ACCEPTING' if state != 'EXIT' else state
            action('project', 'RESERVE-STOP', '停止接單，商品反灰，補足準備金', dict(track=track, balance=states[track]['reserve_balance']))
        if states[track]['exposure'] > states[track]['exposure_limit']:
            state = 'PAUSED' if state == 'NORMAL' else state
            action('project', 'EXPOSURE-PAUSE', '曝險超過可用預算，停止新的採購與承諾', dict(track=track, exposure=states[track]['exposure'], limit=states[track]['exposure_limit']))
        if track == 'B' and states[track]['in_transit']['remaining'] <= 0:
            state = 'PAUSED' if state == 'NORMAL' else state
            action('project', 'B-IN-TRANSIT', '在途額度已滿，商品反灰，暫停新增接單', states[track]['in_transit'])
        if track == 'A' and states[track]['actual_loss'] >= 6000:
            state = 'EXIT'
            action('project', 'A-LOSS-EXIT', '全案停止採購、補貨與廣告，剩餘庫存出清', dict(track=track, actual_loss=states[track]['actual_loss']))
        if track == 'B' and day >= 56 and (m['accepted'] - m['cancelled'] < 8 or low_reserve):
            state = 'EXIT'
            action('project', 'B56-1', '處理在途訂單後全案撤離', dict(track=track, effective_orders=m['accepted'] - m['cancelled']))
        for s in [s for s in p['skus'] if s['track'] == track]:
            sku_rows = [o for o in rows if o['sku'] == s['sku']]
            sm = metrics(sku_rows, as_of)
            pending |= track == 'A' and sm['matured'] < 15
            loss = realized_loss([o for o in orders if o['sku'] == s['sku']], [f for f in flows if f['sku'] == s['sku']]) + inventory_loss([i for i in p['inventory'] if i['sku'] == s['sku']])
            if track == 'A' and (loss >= 2000 or s['tuning_rounds'] >= 2):
                action(s['sku'], 'A14-1', '停止進貨，剩餘庫存出清', dict(loss=money(loss), tuning_rounds=s['tuning_rounds']))
            elif (sm['return_rate'] or 0) >= 0.05 or (sm['defect_rate'] or 0) >= 0.05:
                action(s['sku'], 'B56-2' if track == 'B' else 'A14-2', '停止進貨，追究供應商責任或撤換貨源', sm)
            elif track == 'A' and day >= 14:
                completed = [o for o in sku_rows if o['is_stranger'] == 'true' and o['status'] == 'kept' and mature(o, as_of)]
                ad = sum(dec(d['ad_spend']) for d in days if d['sku'] == s['sku'] and d['round'] == config['current_round'])
                profit = actual_profit(p, rates, completed, as_of)
                avg = (profit - ad) / len(completed) if completed else None
                evidence = dict(**sm, avg_profit_after_ads=money(avg) if avg is not None else None)
                if len(completed) >= 15 and avg > 0:
                    action(s['sku'], 'A14-3', '驗證成功，僅用已撥款淨營收補貨', evidence)
                elif len(completed) >= 15:
                    action(s['sku'], 'A14-4', '停止廣告改自然流，或調整客單價與組合', evidence)
                else:
                    clicks = sum(int(dec(d['clicks'])) for d in days if d['sku'] == s['sku'] and d['round'] == config['current_round'])
                    evidence['clicks'] = clicks
                    if clicks >= 300:
                        action(s['sku'], 'A14-5', '價格、首圖、組合三選一調整，重測七天；等待成熟不增加調優輪數', evidence)
                    else:
                        action(s['sku'], 'A14-6', '樣本不足，延長七天或優化標題；廣告累計仍受上限約束', evidence)
        track_pending = m['matured'] < m['accepted'] or m['matured'] == 0
        pending |= track_pending
        if track == 'B' and day >= 56 and not track_pending and not any(a['rule'] == 'B56-2' and a['scope'] in [s['sku'] for s in p['skus'] if s['track'] == track] for a in actions):
            if m['completed'] >= 20 and avg >= 30 and (m['supplier_fulfillment_rate'] or 0) >= 0.9 and m['cancel_rate'] < 0.05:
                action('project', 'B56-4', '繼續擴大，已撥款利潤滾入下一輪', dict(track=track, **m))
            else:
                action('project', 'B56-5', '準備金足額，僅調整單一變數再測四週', dict(track=track, **m))
    if state != 'NORMAL':
        actions = [a for a in actions if a['rule'] not in ('A14-3', 'A14-5', 'A14-6', 'B56-4', 'B56-5')]
    actions.sort(key=lambda a: (a['scope'] != 'project', a['scope'], a['rule']))
    return dict(global_state=state, actions=actions, maturity='PENDING' if pending else 'MATURED')


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(1, f'參數錯誤：{message}\n')


def main():
    parser = Parser(description=__doc__)
    parser.add_argument('--params', required=True)
    for name in ('orders', 'cashflow', 'daily', 'rates'):
        parser.add_argument('--' + name)
    parser.add_argument('--as-of', default=date.today().isoformat())
    args = parser.parse_args()
    args.rates = args.rates or str(Path(__file__).with_name('rates.json'))
    inputs = Inputs()
    as_of = inputs.day(args.as_of, 'arguments', None, 'as_of')
    p = inputs.load_json(args.params)
    rates = inputs.load_json(args.rates)
    inputs.params(p, args.params)
    inputs.rates(rates, p, args.rates, as_of)
    config_valid = not inputs.errors
    ledgers = {kind: inputs.csv(getattr(args, kind), kind) for kind in HEADERS}
    supplied = [kind for kind in HEADERS if getattr(args, kind)]
    if supplied and len(supplied) != 3:
        for kind in HEADERS:
            if kind not in supplied:
                inputs.error('arguments', None, kind, '事後判讀須同時提供三份帳本')
    if config_valid:
        for kind, rows in ledgers.items():
            inputs.rows(kind, rows, getattr(args, kind), p, as_of)
    result = dict(meta={'as_of': args.as_of, 'warnings': [],
                        'inputs': {name: getattr(args, name) for name in ('params', 'orders', 'cashflow', 'daily', 'rates')}},
                  unit_economics=None, ledger_state=None, verdict=None, errors=inputs.errors)
    if inputs.errors:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
        return 2
    rate_text = json.dumps(rates, ensure_ascii=False, sort_keys=True)
    warnings = [f'費率 {name} 查核已超過 30 天，請至賣家中心確認' for name, rate in sorted(rates.items())
                if (date.fromisoformat(args.as_of) - date.fromisoformat(rate['checked_on'])).days > 30]
    result['meta'].update(rates=rates, rates_version=hashlib.sha256(rate_text.encode()).hexdigest(), warnings=warnings)
    result['unit_economics'] = economics(p, rates)
    if args.orders:
        orders, flows, days = (ledgers[k] for k in ('orders', 'cashflow', 'daily'))
        result['ledger_state'] = ledger(p, orders, flows, as_of)
        result['verdict'] = verdict(p, rates, orders, flows, days, result['ledger_state'], as_of)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
