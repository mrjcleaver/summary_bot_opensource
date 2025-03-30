## Development
Windows
1. IDE Debugpy connection - connect directly in launch.json to docker-host:5678
2. Logs - 

## Production
Windows
1. Proxy ```fly proxy 5678:5678```
2. Console ```fly console```
  sh diagnostics/
3. Console Logs 
  ```fly logs``` or
  +  [Fly Logs Dashboard](https://fly-metrics.net/d/fly-logs/fly-logs?from=now-1h&to=now&var-app=summary-bot-aparine&var-instance=All&orgId=1017766&var-query=) 
4. Deploy ```fly deploy --build-arg INSTALL_DEV=true```
5. Start https://fly.io/apps/summary-bot-aparine/machines 

Note: https://github.com/microsoft/debugpy/issues/1252
debugpy does not support IPV6. Fly.io only supports IPV6.

The solution shown (and installed here) uses:
1. fly proxy tunnelling between your dev machine and the remote container running your app
2. bridges 6tunnel running on the remote container tunnelling between the inbound IPV6 traffic to the Python IPV4-only version of debugpy.





READ THIS FIRST
* Fly Env Var Precedence
(!) Your fly.toml overrides the command line
✅ fly.toml [env] (strongest)
✅ Secrets (fly secrets)
⚠️ --env on fly deploy (weakest — only works if nothing above exists)




Easiest is to access the remote logs:

``fly logs``


Optional: Debug mode environment toggle
To control debugpy at runtime, you can still pair this with a runtime ENV variable:

``fly secrets set DEBUGPY_ENABLE=true ENV=development``


Then attach your IDE’s remote debugger to localhost:5678.


``fly proxy 5678:5678``


Now let’s get **VS Code** to connect to the remote Python process running `debugpy`.

---

### ✅ 1. Make sure your app is listening for the debugger

Somewhere early in your `main.py` (guarded by `DEBUGPY_ENABLE`), you should have:

```python
import debugpy
debugpy.listen(("0.0.0.0", 5678))
print("🪛 Waiting for debugger attach on port 5678...")
# Optional — pause here until debugger is attached
# debugpy.wait_for_client()
```

Then deploy with:
```bash
fly deploy --env DEBUGPY_ENABLE=true
```

---

### ✅ 2. Create a VS Code debug config

Open your `.vscode/launch.json` (or create one), and add this:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Attach to Fly Remote",
      "type": "python",
      "request": "attach",
      "connect": {
        "host": "localhost",
        "port": 5678
      },
      "pathMappings": [
        {
          "localRoot": "${workspaceFolder}",
          "remoteRoot": "/app"
        }
      ],
      "justMyCode": false
    }
  ]
}
```

#### 🔍 Explanation
* `host: "localhost"` — thanks to `fly proxy`, this connects to your remote app.
* `port: 5678` — where `debugpy` is listening.
* `remoteRoot: "/app"` — this is the working dir in your Docker image (`WORKDIR /app`).
* `localRoot: "${workspaceFolder}"` — your local VS Code project path.

---

### ✅ 3. Attach the debugger

1. In VS Code, open the Run & Debug panel.
2. Choose **"Attach to Fly Remote"**.
3. Click the green ► start button.
4. 🎯 Your app should pause if it’s running `debugpy.wait_for_client()` — or you can add breakpoints.

--

Check the remote machine
`` printenv | egrep 'ENV|FLY_MACHINE_ID|DEBUG'``
FLY_MACHINE_ID=2874577c072558
DEBUGPY_ENABLE=false
ENV=production

I did this:
(.venv) PS summary_bot_opensource>``fly deploy --build-arg INSTALL_DEV=true --env DEBUGPY_ENABLE=true --env ENV=development``

But see this:
```
root@2874577c072558:/app# printenv | egrep 'ENV|FLY_MACHINE_ID|DEBUG'
FLY_MACHINE_ID=2874577c072558
DEBUGPY_ENABLE=false
ENV=production
```

This is a quirk in Fly.io: **`--env` flags in `fly deploy` don’t override existing env vars that are already set as secrets or in your `fly.toml`**.

That means:
* You probably have `DEBUGPY_ENABLE=false` and `ENV=production` **defined in `fly.toml` or as Fly secrets**.
* These override anything passed via `--env` on deploy.

---

### ✅ Fix Options

#### 🔧 **Option 1: Update your `fly.toml` for dev builds**
Edit `fly.toml` to temporarily override those vars:

```toml
[env]
ENV = "development"
DEBUGPY_ENABLE = "true"
```

Then just:
```bash
fly deploy --build-arg INSTALL_DEV=true
```

After you're done debugging, revert the `fly.toml` changes.

---

#### 🔧 **Option 2: Use `fly secrets unset` and let `--env` work**

If you've previously set those as secrets (check with `fly secrets list`), remove them:

```bash
fly secrets unset DEBUGPY_ENABLE ENV
```

Then redeploy with:
```bash
fly deploy --build-arg INSTALL_DEV=true --env DEBUGPY_ENABLE=true --env ENV=development
```

Now `--env` will work as expected since nothing is overriding it.

---

### 🔍 How to confirm
After redeploying, SSH into the instance:

```bash
fly ssh console
printenv | egrep 'DEBUG|ENV'
```

You should see:

```bash
DEBUGPY_ENABLE=true
ENV=development
```

---
