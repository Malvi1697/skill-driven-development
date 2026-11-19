# Security

## Reporting a vulnerability

Please do not open a public issue. Use GitHub's private vulnerability
reporting for this repository: the "Report a vulnerability" button under the
Security tab.

## What counts

- A way to change project files without a project skill in use that is not
  listed under "Known gaps" in the README.
- Hook input that makes the hook script run a command or write a file it
  should not.
- A way to make the hook script leak file contents into its messages.

Ways around the rule that the README already lists as known gaps are not
vulnerabilities; improvements to them are welcome as ordinary pull requests.
