import copy
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / 'scripts/shopee_calc.py'
ORDERS = 'order_id track round sku is_stranger accepted_on status completed_on bank_settled_on refund_settled_on price shipping cost_id estimated_cost actual_cost return_loss defect purchased disposed realized_loss cancel_reason'.split()
CASH = 'date track sku category direction estimated_twd actual_twd uses_reserve cost_id order_id'.split()
DAILY = 'date track round sku change impressions clicks ctr ad_spend orders received_amount in_transit notes'.split()


def params(track='A'):
    return {'plan': 1, 'category': 'default', 'return_rate': 0,
            'per_return_loss': 60, 'fx': 0.22, 'wholesale_discount': 0.6,
            'auto_ad': False, 'inventory': [],
            'tracks': {track: {'budget': 20000 if track == 'A' else 15000,
                              'reserve_requirement': 3000 if track == 'A' else 2000,
                              'in_transit_cap': 8000, 'current_round': '1',
                              'rounds': {'1': '2026-09-17'}}},
            'skus': [{'sku': 's', 'track': track, 'price': 200, 'shipping': 0,
                      'landed_cost': 71, 'conversion_rate': 0.03,
                      'promotion': 0, 'gift': 0, 'packaging': 0, 'preorder_fee': 0,
                      'tuning_rounds': 0,
                      'items': [{'retail_jpy': 0, 'domestic_shipping_jpy': 0,
                                 'international_shipping': 71, 'import_tax': 0, 'units': 1}]}]}


def order(i=0, **updates):
    row = dict.fromkeys(ORDERS, '')
    row.update(order_id=str(i), track='A', round='1', sku='s', is_stranger='true',
               accepted_on='2026-09-17', status='kept', completed_on='2026-09-20',
               bank_settled_on='2026-09-28', price=200, shipping=0, cost_id=f'c{i}',
               estimated_cost=71, actual_cost=71, return_loss=0, defect='false',
               purchased='true', disposed='false', realized_loss=0)
    row.update(updates)
    return row


def cash(**updates):
    row = dict(date='2026-09-18', track='A', sku='s', category='procurement',
               direction='out', estimated_twd=0, actual_twd='', uses_reserve='false',
               cost_id='', order_id='')
    row.update(updates)
    return row


def daily(**updates):
    row = dict(date='2026-09-18', track='A', round='1', sku='s', change='',
               impressions=1000, clicks=100, ctr=0.1, ad_spend=0, orders=0,
               received_amount=0, in_transit=0, notes='')
    row.update(updates)
    return row


class CLIContract(unittest.TestCase):
    def run_cli(self, p=None, orders=None, cashflow=None, days=None, rates=None,
                as_of='2026-11-11', omit=(), drop=None, repeat=False):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            pf = directory / 'params.json'
            pf.write_text(json.dumps(p or params()), encoding='utf-8')
            command = [sys.executable, str(CLI), '--params', str(pf), '--as-of', as_of]
            paths = [pf]
            for name, rows, columns in [('orders', orders, ORDERS), ('cashflow', cashflow, CASH), ('daily', days, DAILY)]:
                if rows is None or name in omit:
                    continue
                path = directory / f'{name}.csv'
                fields = [c for c in columns if (name, c) != drop]
                with path.open('w', encoding='utf-8-sig', newline='') as stream:
                    writer = csv.DictWriter(stream, fields, extrasaction='ignore')
                    writer.writeheader()
                    writer.writerows(rows)
                command += ['--' + name, str(path)]
                paths.append(path)
            if rates is not None:
                path = directory / 'rates.json'
                path.write_text(json.dumps(rates), encoding='utf-8')
                command += ['--rates', str(path)]
                paths.append(path)
            before = [hashlib.sha256(f.read_bytes()).hexdigest() for f in paths]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertTrue(result.stdout, result.stderr)
            payload = json.loads(result.stdout)
            after = [hashlib.sha256(f.read_bytes()).hexdigest() for f in paths]
            second = subprocess.run(command, capture_output=True, text=True) if repeat else None
            return result, payload, before, after, second

    def good(self, **kwargs):
        result, data, *_ = self.run_cli(**kwargs)
        self.assertEqual(result.returncode, 0, data)
        self.assertEqual(data['errors'], [])
        return data

    def test_expected_profit(self):
        p = params()
        p['return_rate'] = 0.1
        data = self.good(p=p)
        self.assertEqual(data['unit_economics']['s']['expected_profit'], 84)
        self.assertIsNone(data['ledger_state'])
        self.assertIsNone(data['verdict'])

    def test_plan_fees(self):
        for plan, expected in [(2, 60), (1, 9)]:
            with self.subTest(plan=plan):
                p = params()
                p['plan'] = plan
                p['skus'][0]['price'] = 150
                self.assertEqual(self.good(p=p)['unit_economics']['s']['program_fee'], expected)

    def test_liquidation_bands(self):
        for cost, band, expected, count in [(60, 'plan2_low', 70.18, 2), (100, 'plan2_fixed', 174.87, 1)]:
            with self.subTest(cost=cost):
                p = params()
                p['plan'] = 2
                p['skus'][0]['landed_cost'] = cost
                result = self.good(p=p)['unit_economics']['s']['liquidation']
                self.assertEqual(result['band'], band)
                self.assertEqual(result['price'], expected)
                self.assertEqual(len(result['candidates']), count)

    def test_payment_shipping(self):
        for shipping, expected in [(0, 5), (60, 6.5)]:
            p = params()
            p['skus'][0]['shipping'] = shipping
            self.assertEqual(self.good(p=p)['unit_economics']['s']['payment_fee'], expected)

    def test_thresholds_and_ad_caps(self):
        for track, profit, flag, cap in [('A', 40, '不碰', 40), ('B', 55, '不准上架', 27.5)]:
            for auto in (False, True):
                with self.subTest(track=track, auto=auto):
                    p = params(track)
                    p['auto_ad'] = auto
                    p['skus'][0]['landed_cost'] = 171 - profit
                    p['skus'][0]['items'][0]['international_shipping'] = 171 - profit
                    s = self.good(p=p)['unit_economics']['s']
                    self.assertIn(flag, s['flags'])
                    self.assertEqual(s['cpa_cap'], cap)
                    if track == 'A':
                        self.assertEqual(s['break_even_cpc'], 1.2)
                        self.assertIn('不可依賴付費廣告', s['flags'])

    def test_mature_cohort_return_rate(self):
        rows = [order(i) for i in range(20)]
        rows.append(order(20, status='returned', refund_settled_on='', completed_on='2026-11-10', bank_settled_on=''))
        data = self.good(orders=rows, cashflow=[], days=[])
        self.assertEqual(data['ledger_state']['A']['metrics']['return_rate'], 0)
        self.assertEqual(data['ledger_state']['A']['metrics']['matured'], 20)

    def test_zero_matured_pending(self):
        data = self.good(orders=[order(bank_settled_on='')], cashflow=[], days=[])
        m = data['ledger_state']['A']['metrics']
        self.assertIsNone(m['return_rate'])
        self.assertEqual(m['return_rate_status'], 'PENDING')

    def test_cancelled_settled_maturity(self):
        rows = [order(status='cancelled', cancel_reason='buyer', purchased='false',
                      completed_on='', bank_settled_on='', refund_settled_on='2026-09-20')]
        data = self.good(orders=rows, cashflow=[], days=[])
        self.assertEqual(data['ledger_state']['A']['metrics']['matured'], 1)

    def test_b_exit_and_quality_precedence(self):
        rows = [order(i, track='B', status='cancelled' if i < 3 else 'kept',
                      cancel_reason='buyer' if i < 3 else '',
                      refund_settled_on='2026-09-28' if i < 3 else '',
                      defect='true' if i == 4 else 'false') for i in range(10)]
        data = self.good(p=params('B'), orders=rows, cashflow=[], days=[])
        v = data['verdict']
        self.assertEqual(v['global_state'], 'EXIT')
        self.assertEqual([a['rule'] for a in v['actions']], ['B56-1', 'B56-2'])
        self.assertEqual(v['actions'][0]['scope'], 'project')

    def test_reserve_pause_blocks_growth(self):
        data = self.good(p=params('B'), orders=[order(i, track='B') for i in range(20)],
                         cashflow=[cash(track='B', category='refund', estimated_twd=500, uses_reserve='true')], days=[])
        self.assertEqual(data['verdict']['global_state'], 'PAUSED')
        self.assertFalse(any(a['rule'] in ('B56-4', 'B56-5', 'A14-3') for a in data['verdict']['actions']))
        self.assertEqual(data['ledger_state']['B']['reserve_balance'], 1500)

    def test_reserve_stop_accepting(self):
        data = self.good(p=params('B'), orders=[order(i, track='B') for i in range(20)],
                         cashflow=[cash(track='B', category='refund', estimated_twd=1100, uses_reserve='true')], days=[],
                         as_of='2026-10-28')
        self.assertEqual(data['verdict']['global_state'], 'STOP_ACCEPTING')

    def test_paid_exposure_once(self):
        data = self.good(p=params('B'), orders=[order(track='B', actual_cost=9000, estimated_cost=9000, bank_settled_on='')],
                         cashflow=[cash(track='B', cost_id='c0', estimated_twd=9000)], days=[])
        s = data['ledger_state']['B']
        self.assertEqual(s['paid_spend'], 9000)
        self.assertEqual(s['unpaid_obligations'], 0)
        self.assertEqual(s['exposure'], 9000)
        self.assertEqual(s['available_cash'], 6000)

    def test_resale_in_transit(self):
        for settled, expected in [('', 100), ('2026-10-10', 0)]:
            rows = [order(0, track='B', status='returned', actual_cost=100, cost_id='same', refund_settled_on='2026-09-29'),
                    order(1, track='B', cost_id='same', actual_cost=100, bank_settled_on=settled)]
            data = self.good(p=params('B'), orders=rows, cashflow=[], days=[])
            self.assertEqual(data['ledger_state']['B']['in_transit']['occupied'], expected)
            self.assertEqual(data['ledger_state']['B']['unpaid_obligations'], 100)

    def test_actual_card_settlement(self):
        data = self.good(p=params('B'), orders=[],
                         cashflow=[cash(track='B', estimated_twd=5000, actual_twd=5080)], days=[])
        self.assertEqual(data['ledger_state']['B']['available_cash'], 9920)
        self.assertEqual(data['ledger_state']['B']['paid_spend'], 5080)

    def test_a14_row1(self):
        for loss, tuning in [(2000, 0), (0, 2)]:
            p = params()
            p['skus'][0]['tuning_rounds'] = tuning
            data = self.good(p=p, orders=[order(defect='true', realized_loss=loss)], cashflow=[], days=[])
            self.assertEqual([a['rule'] for a in data['verdict']['actions'] if a['scope'] == 's'], ['A14-1'])

    def test_a14_row2_always_on(self):
        p = params()
        p['tracks']['A']['rounds']['1'] = '2026-11-01'
        rows = [order(i, accepted_on='2026-11-01', completed_on='', bank_settled_on='',
                      status='returned' if i == 0 else 'kept',
                      refund_settled_on='2026-11-02' if i == 0 else '') for i in range(20)]
        data = self.good(p=p, orders=rows, cashflow=[], days=[], as_of='2026-11-03')
        self.assertEqual(data['verdict']['actions'][0]['rule'], 'A14-2')
        self.assertEqual(data['verdict']['maturity'], 'PENDING')

    def test_a14_row3(self):
        data = self.good(orders=[order(i) for i in range(15)], cashflow=[], days=[daily(ad_spend=100, clicks=400)])
        self.assertEqual(data['verdict']['actions'][0]['rule'], 'A14-3')
        self.assertEqual(data['verdict']['actions'][0]['evidence']['avg_profit_after_ads'], 93.33)

    def test_a14_row4(self):
        data = self.good(orders=[order(i) for i in range(15)], cashflow=[], days=[daily(ad_spend=1500, clicks=400)])
        self.assertEqual(data['verdict']['actions'][0]['rule'], 'A14-4')
        self.assertEqual(data['verdict']['actions'][0]['evidence']['avg_profit_after_ads'], 0)

    def test_a14_row5(self):
        data = self.good(orders=[order(i) for i in range(14)], cashflow=[], days=[daily(clicks=300)])
        self.assertEqual(data['verdict']['actions'][0]['rule'], 'A14-5')

    def test_a14_row6(self):
        data = self.good(orders=[order(i) for i in range(14)], cashflow=[], days=[daily(clicks=299)])
        self.assertEqual(data['verdict']['actions'][0]['rule'], 'A14-6')

    def test_a_maturity_gate(self):
        data = self.good(orders=[order(i) for i in range(14)], cashflow=[], days=[])
        self.assertEqual(data['verdict']['maturity'], 'PENDING')
        self.assertNotIn('A14-3', [a['rule'] for a in data['verdict']['actions']])

    def test_rates_staleness_metadata(self):
        rates = json.loads((ROOT / 'scripts/rates.json').read_text())
        rates['payment']['checked_on'] = '2026-10-11'
        data = self.good(rates=rates)
        self.assertEqual(len(data['meta']['warnings']), 1)
        self.assertIn('payment', data['meta']['warnings'][0])
        self.assertEqual(data['meta']['rates']['payment']['checked_on'], '2026-10-11')
        self.assertIn('rates_version', data['meta'])

    def test_input_errors(self):
        cases = [dict(drop=('orders', 'sku'), column='sku', row=0),
                 dict(orders=[order(price='oops')], column='price', row=1),
                 dict(omit=('daily',), column='daily', row=None)]
        for case in cases:
            with self.subTest(case=case):
                case = dict(case)
                column, row = case.pop('column'), case.pop('row')
                inputs = dict(orders=[order()], cashflow=[], days=[])
                inputs.update(case)
                result, data, *_ = self.run_cli(**inputs)
                self.assertEqual(result.returncode, 2, data)
                self.assertTrue(any(e['column'] == column and e['row'] == row and e['file'] for e in data['errors']), data)
                for key in ('unit_economics', 'ledger_state', 'verdict'):
                    self.assertIsNone(data[key])

    def test_irrevocable_inventory_loss(self):
        p = params()
        p['inventory'] = [dict(sku='s', track='A', units=2, book_cost_per_unit=4000,
                               est_net_recovery_per_unit=500, irrevocable=True)]
        data = self.good(p=p, orders=[], cashflow=[], days=[])
        self.assertEqual(data['ledger_state']['A']['actual_loss'], 7000)
        self.assertEqual(data['ledger_state']['A']['exposure'], 8000)
        self.assertEqual(data['verdict']['global_state'], 'EXIT')
        self.assertEqual(data['verdict']['actions'][0]['rule'], 'A-LOSS-EXIT')

    def test_reserve_draw_and_topup(self):
        data = self.good(p=params('B'), orders=[], days=[], cashflow=[
            cash(track='B', category='refund', uses_reserve='true', estimated_twd=500, actual_twd=520),
            cash(track='B', category='reserve_topup', direction='in', estimated_twd=300)])
        self.assertEqual(data['ledger_state']['B']['reserve_balance'], 1780)
        self.assertEqual(data['ledger_state']['B']['reserve_gap'], 220)

    def test_b56_expand_and_retest(self):
        for failed, expected in [(0, 'B56-4'), (3, 'B56-5')]:
            with self.subTest(failed=failed):
                rows = [order(i, track='B', cancel_reason='supplier' if i < failed else '') for i in range(20)]
                # A cancelled procurement attempt is still an accepted stranger order.
                rows += [order(20 + i, track='B', status='cancelled', purchased='false', cancel_reason='supplier',
                               bank_settled_on='', completed_on='', refund_settled_on='2026-09-28') for i in range(failed)]
                if failed:
                    # 3 failures / 20 attempts = 15%; the kept orders already include 3 unpurchased successes.
                    for row in rows[:3]:
                        row['purchased'] = 'false'
                data = self.good(p=params('B'), orders=rows, cashflow=[], days=[daily(track='B', ad_spend=100)])
                self.assertIn(expected, [a['rule'] for a in data['verdict']['actions']])
                if failed:
                    self.assertEqual(data['ledger_state']['B']['metrics']['supplier_fulfillment_rate'], 0.85)

    def test_b42_never_expand(self):
        data = self.good(p=params('B'), orders=[order(i, track='B') for i in range(20)], cashflow=[], days=[], as_of='2026-10-28')
        self.assertFalse(any(a['rule'] in ('B56-4', 'B56-5') for a in data['verdict']['actions']))

    def test_read_only(self):
        _, _, before, after, _ = self.run_cli(orders=[order()], cashflow=[cash()], days=[daily()])
        self.assertEqual(before, after)

    def test_deterministic_stdout(self):
        result, _, _, _, second = self.run_cli(orders=[order()], cashflow=[], days=[], repeat=True)
        self.assertEqual(result.stdout, second.stdout)

    def test_b_maturity_and_strangers(self):
        rows = [order(i, track='B') for i in range(20)]
        rows.append(order(30, track='B', status='returned', bank_settled_on='', completed_on='2026-11-10'))
        data = self.good(p=params('B'), orders=rows, cashflow=[], days=[])
        self.assertEqual(data['verdict']['maturity'], 'PENDING')
        self.assertEqual(data['verdict']['actions'], [])
        rows[-1]['is_stranger'] = 'false'
        rows[-1]['defect'] = 'true'
        data = self.good(p=params('B'), orders=rows, cashflow=[], days=[])
        self.assertEqual(data['verdict']['maturity'], 'MATURED')
        self.assertIn('B56-4', [a['rule'] for a in data['verdict']['actions']])

    def test_input_round_and_collection(self):
        result, data, *_ = self.run_cli(orders=[order(accepted_on='2026-10-02'), order(1, price='NaN')],
                                       cashflow=[cash(estimated_twd=-1)], days=[], drop=('daily', 'clicks'))
        self.assertEqual(result.returncode, 2)
        columns = {e['column'] for e in data['errors']}
        self.assertTrue({'round', 'price', 'estimated_twd', 'clicks'} <= columns, data)

    def test_two_track_severity(self):
        p = params('B')
        p['tracks']['A'] = params()['tracks']['A']
        a = copy.deepcopy(params()['skus'][0])
        a['sku'] = 'a'
        p['skus'].append(a)
        rows = [order(i, track='B') for i in range(20)]
        rows += [order(100 + i, sku='a') for i in range(15)]
        data = self.good(p=p, orders=rows, cashflow=[
            cash(track='B', category='refund', estimated_twd=1100, uses_reserve='true'),
            cash(sku='a', category='refund', estimated_twd=500, uses_reserve='true')], days=[], as_of='2026-10-28')
        self.assertEqual(data['verdict']['global_state'], 'STOP_ACCEPTING')
        self.assertFalse(any(a['rule'] in ('A14-3', 'A14-5', 'A14-6', 'B56-4', 'B56-5') for a in data['verdict']['actions']))

    def test_exposure_and_transit_caps(self):
        for cost, expected_rule in [(9000, 'B-IN-TRANSIT'), (14000, 'EXPOSURE-PAUSE')]:
            with self.subTest(cost=cost):
                data = self.good(p=params('B'), orders=[order(track='B', bank_settled_on='', actual_cost=cost)],
                                 cashflow=[], days=[], as_of='2026-10-28')
                self.assertEqual(data['verdict']['global_state'], 'PAUSED')
                self.assertIn(expected_rule, [a['rule'] for a in data['verdict']['actions']])

    def test_b_landed_cost_precision(self):
        p = params('B')
        p['skus'][0]['items'] = [dict(retail_jpy=1001, domestic_shipping_jpy=10,
                                     international_shipping=11, import_tax=2, units=3)]
        s = self.good(p=p)['unit_economics']['s']
        self.assertEqual(s['order_cost'], 448.04)
        self.assertEqual(s['item_costs'][0]['unit_cost'], 149.35)

    def test_malformed_nested_inputs(self):
        for key in ('sku', 'round', 'track', 'extra_rate'):
            with self.subTest(key=key):
                p = params()
                rates = None
                if key == 'sku':
                    p['skus'][0]['sku'] = []
                elif key == 'round':
                    p['tracks']['A']['current_round'] = []
                elif key == 'track':
                    p['skus'][0]['track'] = []
                else:
                    rates = json.loads((ROOT / 'scripts/rates.json').read_text())
                    rates['extra'] = {'value': 0.1, 'effective_from': 'bad', 'checked_on': 'bad'}
                result, data, *_ = self.run_cli(p=p, rates=rates)
                self.assertEqual(result.returncode, 2)
                self.assertTrue(data['errors'])

    def test_daily_ctr_required(self):
        result, data, *_ = self.run_cli(orders=[], cashflow=[], days=[], drop=('daily', 'ctr'))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(data['errors'][0]['column'], 'ctr')

    def test_integral_click_values(self):
        data = self.good(orders=[], cashflow=[], days=[daily(clicks='300.0')])
        self.assertEqual(data['verdict']['actions'][0]['rule'], 'A14-5')

    def test_f1_terminal_orders_require_actual_cost(self):
        for track in ('A', 'B'):
            for status in ('kept', 'returned'):
                with self.subTest(track=track, status=status):
                    result, data, *_ = self.run_cli(
                        p=params(track), orders=[order(track=track, status=status,
                                                     purchased='false', actual_cost='')],
                        cashflow=[], days=[], as_of='2026-10-20')
                    self.assertEqual(result.returncode, 2, data)
                    self.assertEqual(result.stderr, '')
                    self.assertTrue(any(e['column'] == 'actual_cost' and e['row'] == 1
                                        for e in data['errors']), data)
                    for key in ('unit_economics', 'ledger_state', 'verdict'):
                        self.assertIsNone(data[key])

    def test_f2_non_stranger_losses_trigger_red_lines(self):
        for column in ('return_loss', 'realized_loss'):
            for loss in (2000, 7000):
                with self.subTest(column=column, loss=loss):
                    rows = [order(i) for i in range(15)]
                    rows.append(order(15, is_stranger='false', status='returned',
                                      refund_settled_on='2026-09-29', defect='true',
                                      **{column: loss}))
                    data = self.good(orders=rows, cashflow=[], days=[])
                    state = data['ledger_state']['A']
                    self.assertEqual(state['actual_loss'], loss)
                    self.assertEqual(state['realized_loss'], loss)
                    self.assertEqual(data['verdict']['global_state'], 'EXIT' if loss == 7000 else 'NORMAL')
                    rules = [a['rule'] for a in data['verdict']['actions']]
                    self.assertIn('A14-1', rules)
                    self.assertEqual('A-LOSS-EXIT' in rules, loss == 7000)
                    self.assertNotIn('A14-2', rules)
                    self.assertEqual(state['metrics']['accepted'], 15)
                    self.assertEqual(state['metrics']['return_rate'], 0)
                    self.assertEqual(state['metrics']['defect_rate'], 0)
                    self.assertEqual(state['metrics']['avg_contribution_after_ads'], 100)

    def test_f3_growth_uses_own_track_state(self):
        cases = [('A', 20, 15, 0, 'B56-4'), ('A', 8, 15, 0, 'B56-5'),
                 ('B', 20, 15, 0, 'A14-3'), ('B', 20, 14, 300, 'A14-5'),
                 ('B', 20, 14, 299, 'A14-6')]
        growth_rules = {'A14-3', 'A14-5', 'A14-6', 'B56-4', 'B56-5'}
        for paused, b_count, a_count, clicks, expected in cases:
            for reverse in (False, True):
                with self.subTest(paused=paused, expected=expected, reverse=reverse):
                    p = params()
                    p['tracks']['B'] = params('B')['tracks']['B']
                    p['skus'][0]['sku'] = 'a'
                    b = copy.deepcopy(params('B')['skus'][0])
                    b['sku'] = 'b'
                    p['skus'].append(b)
                    if reverse:
                        p['tracks'] = dict(reversed(list(p['tracks'].items())))
                    rows = [order(i, sku='a') for i in range(a_count)]
                    rows += [order(100 + i, track='B', sku='b') for i in range(b_count)]
                    data = self.good(p=p, orders=rows, days=[daily(sku='a', clicks=clicks)],
                                     cashflow=[cash(track=paused, sku=paused.lower(), category='refund',
                                                    estimated_twd=500, uses_reserve='true')])
                    self.assertEqual(data['verdict']['global_state'], 'PAUSED')
                    matched_growth = [a['rule'] for a in data['verdict']['actions'] if a['rule'] in growth_rules]
                    self.assertEqual(matched_growth, [expected])

    def test_f4_reserve_spend_excluded_from_exposure(self):
        for track in ('A', 'B'):
            for uses_reserve in (True, False):
                for topup in (0, 520):
                    with self.subTest(track=track, uses_reserve=uses_reserve, topup=topup):
                        p = params(track)
                        config = p['tracks'][track]
                        limit = config['budget'] - config['reserve_requirement']
                        flows = [cash(track=track, category='other', estimated_twd=limit - 100, actual_twd=limit),
                                 cash(track=track, category='refund', estimated_twd=500, actual_twd=520,
                                      uses_reserve='true' if uses_reserve else 'false')]
                        if topup:
                            flows.append(cash(track=track, category='reserve_topup', direction='in', estimated_twd=topup))
                        data = self.good(p=p, orders=[], cashflow=flows, days=[], as_of='2026-10-28')
                        state = data['ledger_state'][track]
                        paid = limit + (0 if uses_reserve else 520)
                        self.assertEqual(state['paid_spend'], paid)
                        self.assertEqual(state['exposure'], paid)
                        self.assertEqual(state['unpaid_obligations'], 0)
                        self.assertEqual(state['available_cash'], config['reserve_requirement'] - 520 + topup)
                        balance = config['reserve_requirement'] - (520 if uses_reserve else 0) + topup
                        self.assertEqual(state['reserve_balance'], balance)
                        rules = [a['rule'] for a in data['verdict']['actions']]
                        self.assertEqual('EXPOSURE-PAUSE' in rules, not uses_reserve)
                        self.assertEqual(data['verdict']['global_state'], 'NORMAL' if uses_reserve and topup else 'PAUSED')
