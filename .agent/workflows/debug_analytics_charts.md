---
description: Debug and fix analytics charts on the analytics page
---

## Workflow: Debug Analytics Charts

1. **Start the FastAPI server**
   ```bash
   # Ensure you are in the project root directory
   uvicorn app.main:app --reload
   ```
   // turbo
2. Open a browser and navigate to `http://localhost:8000/dashboard/analytics`.
3. Open the developer console (F12) and look for any JavaScript errors, especially related to `Chart.js` or `Alpine.js`.
4. Verify that the API endpoints used by the page return valid JSON:
   - `GET /api/analytics/temperature`
   - `GET /api/analytics/heartrate`
   - `GET /api/analytics/alerts`
   You can test them directly in the browser or with `curl`.
5. If any endpoint returns an error, inspect the corresponding route in `app/routes/api.py` and fix the database query or return structure.
6. If you see a race‑condition error that Chart.js is undefined, modify `app/templates/dashboard/analytics.html`:
   - Remove the custom `waitForChartJS` function.
   - Add the Chart.js script **before** the Alpine component initialization.
   Example change:
     ```html
     <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
     <div x-data="analytics" x-init="init()">
     ```
7. Ensure the static files are correctly mounted. In `app/main.py` add:
   ```python
   app.mount("/static", StaticFiles(directory="app/static"), name="static")
   ```
8. Refresh the page and confirm that all canvas elements (`tempTrendChart`, `hrDistChart`, `alertTypeChart`, `alertTrendChart`) display charts.
9. (Optional) Add a fallback demo dataset in the JavaScript functions if the API returns empty data (already present in the template).
10. Commit the changes and push to version control.

---

**Notes**
- The `// turbo` annotation on step 2 will automatically run the `uvicorn` command when you approve it.
- This workflow assumes you have Python 3.11+ and the required dependencies installed (`fastapi`, `uvicorn`, etc.).
- If the server fails to start, check `app/__init__.py` for the `create_app` function and ensure `app/main.py` exists (see step 1).
