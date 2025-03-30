## Setting up 
I'm on a Windows 11 machine.
You can use open-fly-env.ps1 to open the various windows.
.env contains secrets

## Deploying to Docker on my LAN
 Currently I have a Docker / Portainer instance inside Proxmox on an enterprise-grade laptop.
 It is unaccessible from the internet. I leave it on 24/7.

Laptop:
* bin/deploy-to-docker-host.sh (uses docker-compose) 

Proxmox console:
* pct enter 100 # enter docker-host
* docker exec -it summary_bot_opensource-summary-bot-1 /bin/bash # enter docker-container hosting bot


## Deploying to Fly.io (Future use)
This is something I don't do at present.

* fly apps create summary-bot-aparine
* fly deploy --build-arg INSTALL_DEV=true
* fly ext sentry create

Run the machine from e.g. https://fly.io/apps/summary-bot-aparine/machines/48eddeef724d08

.\fly-set-secrets.ps1 

### To Debug 
fly secrets set DEBUGPY_ENABLE=true 

Bonus: Secure fly proxy to debug
On your local machine:

bash
``fly proxy 5678:5678``

Then attach your IDE’s remote debugger to localhost:5678.

## In fly.toml:

* build.args.INSTALL_DEV = "false": Tells Fly's remote builder not to install dev dependencies unless overridden during deploy.
* env.DEBUGPY_ENABLE = "false": Prevents debugpy from starting by default.
* env.DEBUGPY_WAIT = will wait for the debugger to connect (hint: don't forget to proxy it)

The second [[services]] block exposes port 5678 internally, not publicly, so you can attach via fly proxy.

### Temporarily enable debugging (from CLI)
 To deploy with debugging enabled: 

````
fly deploy --build-arg INSTALL_DEV=true \
 --env DEBUGPY_ENABLE=true \
 --env ENV=development
````