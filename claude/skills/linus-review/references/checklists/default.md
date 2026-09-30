#### Correctness
Is the logic correct? Are there missing boundary conditions?
Are exceptions handled properly?
Is it thread-safe in concurrent scenarios?

#### Security
Are there security vulnerabilities such as SQL injection or XSS?
Is sensitive information handled correctly?
Is permission validation complete?
Are record/tenant ids from the request checked against the current user/tenant (IDOR), rather than trusted as-is?
Do outbound requests built from user input restrict scheme, host, and private-network targets (SSRF)?
Are file uploads validated server-side (type, generated storage name, destination) rather than trusted by client filename/MIME?
Does token verification pin the signature algorithm and check `exp`, `aud`, and `iss`?
Are secrets kept out of source and committed config?

#### Performance
Are there obvious performance issues (e.g., N+1 queries, unnecessary loops)?
Are resources properly released?

#### Maintainability
Is the code clear and easy to understand?
Do names accurately express intent?
Does it follow the project’s existing code style and architecture patterns?

#### Test Coverage
Do critical logic paths have corresponding test cases?
Do test cases cover boundary conditions?
