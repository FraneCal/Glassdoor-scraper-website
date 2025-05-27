import streamlit as st
import pandas as pd
import json
import subprocess
import os
import time
import itertools

JOBS_FILE = "../jobs.json"
SCRAPER_FILE = "scraper_sb.py"
STOP_FILE = "stop_signal.txt"

# Clear jobs file at startup
open(JOBS_FILE, "w", encoding="utf-8").write("[]")

def load_jobs(filepath=JOBS_FILE):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def run_scraper(job_name, location):
    if os.path.exists(STOP_FILE):
        os.remove(STOP_FILE)
    return subprocess.Popen(["python", SCRAPER_FILE, job_name, location])

def prepare_downloads(data):
    df = pd.DataFrame(data)
    csv = df.to_csv(index=False).encode("utf-8")
    json_str = json.dumps(data, indent=2).encode("utf-8")
    return csv, json_str

def main():
    st.set_page_config(page_title="Job Listings", layout="wide")
    st.title("📋 Glassdoor Job Scraper")

    st.session_state.setdefault("scraping", False)
    st.session_state.setdefault("job_proc", None)
    st.session_state.setdefault("has_scraped", False)

    with st.form("scrape_form"):
        job_name = st.text_input("🔍 Job Name", "", placeholder="e.g. Python Developer")
        location = st.text_input("📍 Location", "", placeholder="e.g. Germany")
        submitted = st.form_submit_button("🚀 Scrape")

        if submitted:
            if not job_name or not location:
                st.warning("Please enter both Job Name and Location.")
            else:
                st.session_state.job_proc = run_scraper(job_name, location)
                st.session_state.scraping = True

    if st.session_state.scraping:
        stop_btn_ph = st.empty()
        table_ph = st.empty()
        progress_ph = st.empty()
        stop_clicked = stop_btn_ph.button("🛑 Stop Scraping")

        progress_bar = progress_ph.progress(0)
        progress_anim = itertools.cycle(range(0, 100, 5))
        last_len = 0

        while True:
            if stop_clicked:
                with open(STOP_FILE, "w") as f:
                    f.write("stop")
                st.warning("Scraping stopped by user.")
                break

            process_done = st.session_state.job_proc.poll() is not None

            jobs = load_jobs()
            jobs_count = len(jobs)

            if jobs:
                table_ph.dataframe(pd.DataFrame(jobs), use_container_width=True)

            # Animate progress bar during scrape
            progress_bar.progress(next(progress_anim))

            if process_done:
                progress_bar.progress(100)
                st.success("Scraping completed.")
                break

            time.sleep(1 if jobs_count != last_len else 2)
            last_len = jobs_count

        stop_btn_ph.empty()
        progress_ph.empty()
        st.session_state.scraping = False
        st.session_state.has_scraped = True

        # Show final results
        jobs = load_jobs()
        if jobs:
            table_ph.dataframe(pd.DataFrame(jobs), use_container_width=True)
            csv, json_str = prepare_downloads(jobs)
            st.download_button("📥 Download CSV", csv, f"{job_name}_{location}.csv", "text/csv")
            st.download_button("📥 Download JSON", json_str, f"{job_name}_{location}.json", "application/json")

    else:
        if st.button("🔁 Refresh Data"):
            st.success("Data refreshed.")

        # Only show data if user has scraped
        if st.session_state.has_scraped:
            jobs = load_jobs()
            if jobs:
                df = pd.DataFrame(jobs)
                st.markdown("### Results")
                st.write(f"Total jobs: {len(df)}")
                st.dataframe(df, use_container_width=True)
                csv, json_str = prepare_downloads(jobs)
                st.download_button("📥 Download CSV", csv, "jobs.csv", "text/csv")
                st.download_button("📥 Download JSON", json_str, "jobs.json", "application/json")
        else:
            st.info("No scraped results yet. Start a scrape to see results.")

if __name__ == "__main__":
    main()