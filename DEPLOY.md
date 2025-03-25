fly apps create summary-bot-aparine

fly deploy --build-arg INSTALL_DEV=true

fly ext sentry create

Run the machine from e.g. https://fly.io/apps/summary-bot-aparine/machines/48eddeef724d08


.\fly-set-secrets.ps1 

### To Debug 
fly secrets set DEBUGPY_ENABLE=true 


Bonus: Secure fly proxy to debug
On your local machine:

bash
``fly proxy 5678:5678``

Then attach your IDE’s remote debugger to localhost:5678.

In fly.toml:

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