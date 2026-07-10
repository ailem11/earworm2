# 🚀 Google Cloud Platform (GCP) Operations Guide for Earworm2

A comprehensive reference for manually triggering deployments, managing secrets, reading logs, and auditing your deployed application on GCP.

## 🗄️ GCP Project Context
*   **Project ID:** `aile-playground`
*   **Service Region:** `us-east1`
*   **Cloud Run Service:** `earworm2`
*   **Active CI/CD Trigger:** `rmgpgab-earworm2-us-east1-...`

---

## 🛠️ 1. How to Manually Trigger a Deployment
If you want to release a new version from your GitHub repository *without* waiting for a push trigger, or to retry a failed build:
1. Go to the [Cloud Build Triggers Dashboard](https://console.cloud.google.com/cloud-build/triggers).
2. Locate the **`rmgpgab-earworm2-us-east1-...`** trigger.
3. Click the **Run** button on the far right of the row.
4. Select the branch you want to build (defaults to `main`) and click **Run Trigger**.

---

## 📝 2. How to Read Server and Deployment Logs
When something isn't working as expected (e.g., Python exceptions, HTTP 500 errors, or build failures), you can inspect two types of logs:

### Viewing Live Python & Flask Server Logs (Cloud Run)
1. Go to the [Cloud Run Dashboard](https://console.cloud.google.com/run).
2. Click on your **`earworm2`** service.
3. Click the **Logs** tab near the top of the service page.
4. You will see a real-time, streamable output of all `print()` statements, Flask `app.logger.debug()` outputs, and requests hitting your server.

### Viewing Build & Docker Compilation Logs (Cloud Build)
1. Go to the [Cloud Build History Dashboard](https://console.cloud.google.com/cloud-build/builds).
2. Click on any specific Build ID to view the full terminal output of your `pip install`, `COPY`, and Docker image compilation.

---

## 🔐 3. How to Rotate or Update Secret API Keys
If you need to change your ACRCloud credentials or add new database keys:
1. Open the [Secret Manager Dashboard](https://console.cloud.google.com/security/secret-manager).
2. Click on the Secret you want to update (e.g., `ACRCLOUD_ACCESS_SECRET`).
3. Click **+ New Version**.
4. Paste the new key string and click **Save**.
5. **Important**: Go to your [Cloud Run Service](https://console.cloud.google.com/run), click **Edit & Deploy New Revision**, go to the **Variables & Secrets** tab, and ensure the secret reference is set to map to the `latest` version (or the specific version ID you just created), then click **Deploy**.

---

## 🖼️ 4. How to Inspect Your Deployed Container Images
To see the actual compiled filesystem versions of your Docker container:
1. Navigate to the [Artifact Registry Dashboard](https://console.cloud.google.com/artifacts).
2. Click on the **`cloud-run-source-deploy`** repository.
3. You will find a list of all images pushed by Cloud Build, tagged by date and git commit SHA.

---

## 🛑 5. How to Manually Turn Off or Restart Your Web App
*   **To Restart:** Navigate to the [Cloud Run Service Dashboard](https://console.cloud.google.com/run), click into your **`earworm2`** service, and click **Edit & Deploy New Revision** at the top. Re-deploying the current image acts as a clean server restart.
*   **To Pause Traffic (Turn Off):** You can set the traffic allocation to **0%** on the latest revision, or click **Delete** on the service page if you want to decommission the server completely.
