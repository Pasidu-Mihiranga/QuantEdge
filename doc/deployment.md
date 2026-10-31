# Deploying the app

The booklet requires Streamlit as the interface and accepts an app that is deployed or runnable locally with one command. `make run` meets the second. A public link is the easier choice for judges.

The app reads `data/artifacts/` only: it needs no secrets, API keys or network data, and it does not need the git tag.

## AWS EC2

`deploy/` installs the app as a service behind nginx, with HTTPS from Let's Encrypt. It works on Ubuntu, Debian and Amazon Linux, and it can be run again for every new release.

**Before the first deploy, in the EC2 console:**

1. Note the instance's **public IPv4 address** and its operating system (user `ubuntu` on Ubuntu, `ec2-user` on Amazon Linux).
2. Under **Security group → Inbound rules**, allow port 22 from your own IP, and ports 80 and 443 from anywhere.
3. Attach an **Elastic IP**, so the link does not change if the instance restarts. It is free while attached to a running instance.
4. Use at least a `t3.small` (2 GB). A 1 GB instance works with the swap file the script adds, but it is slow to install.

**Deploy from your computer, in the repository folder:**

```bash
chmod 400 qunatage.pem
deploy/deploy.sh <public-ip> ubuntu qunatage.pem
```

The script sends only files git tracks or would track, so keys never leave your machine. It finishes with a health check, then the app is at <https://quantedge.gmora.dev>.

The hostname's A record must point at the server first. Certbot then issues the Let's Encrypt certificate on the first release, puts it back on later ones, and renews it through `certbot.timer`. Requests by IP address redirect to the hostname.

**Later:**

| Task | Command, on the server |
|---|---|
| Is it running? | `systemctl status quantedge` |
| Recent errors | `journalctl -u quantedge -n 50` |
| Restart | `sudo systemctl restart quantedge` |
| Check certificate renewal | `sudo certbot renew --dry-run --cert-name quantedge.gmora.dev` |

To release a new version, run `deploy/deploy.sh` again.

## Streamlit Community Cloud (free fallback)

1. Push the branch to GitHub.
2. Sign in at https://share.streamlit.io with a GitHub account that can see the repository.
3. Choose **Create app**, then the repository, the branch and the main file `app/Home.py`.
4. Under **Advanced settings**, choose **Python 3.12**.
5. Deploy, then open every page once and check the verdict on the first page.

An idle app sleeps and wakes on the next visit, so open it shortly before judging.
