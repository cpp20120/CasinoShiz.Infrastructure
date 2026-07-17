# Security policy

## Reporting

Do not report credentials, tokens, host addresses, private keys or production
configuration in public issues.

Revoke any credential immediately if it is accidentally committed.

## Repository rules

- Never commit plaintext Kubernetes Secrets.
- Never commit age private keys.
- Never commit kubeconfig files.
- Never commit GitHub tokens, Telegram tokens or database passwords.
- Production images must use immutable tags or digests.
- Infrastructure changes must pass repository validation before deployment.

## Incident response

For a leaked credential:

1. revoke or rotate the credential;
2. remove the secret from the current tree;
3. purge it from Git history if necessary;
4. rotate dependent credentials;
5. verify audit logs;
6. document the incident without reproducing the secret.
