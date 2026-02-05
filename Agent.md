# Project Overview: HBUT Educational Mini Program

This project is a WeChat Mini Program (frontend) and Python FastAPI (backend) application designed to help students of Hubei University of Technology (HBUT) access their schedules, grades, and class rankings.

## Architecture

### Backend (`backend/main.py`)
A **FastAPI** application acting as a proxy and scraper between the Mini Program and the HBUT Educational Administration System (hbut.jw.chaoxing.com). **Now deployed on Alibaba Cloud Function Compute (FC) to prevent IP blocking.**

-   **Tech Stack**: Python, FastAPI, Requests, BeautifulSoup4, ddddocr (OCR), Crypto (AES).
-   **Key Features**:
    -   **Login Proxy**: simulating the official login process, including password encryption (AES) and execution flow.
    -   **Auto-CAPTCHA**: Uses `ddddocr` to attempt automatic login. Falls back to manual input if it fails.
    -   **Data Scraping**: Fetches and parses HTML/JSON for Timetables, Grades, and Rankings.
    -   **Serverless & Stateless**: Uses AES encryption to store session state (Cookies) inside the `user_token` itself. No database or Redis required.
    -   **IP Rotation**: Leveraging Alibaba Cloud's IP pool to avoid IP bans from the school system.
-   **API Endpoints**:
    -   `POST /api/login`: Handles login (Auto & Manual modes).
    -   `GET /api/captcha`: Fetches a fresh captcha for manual input.
    -   `POST /api/grades`: Parses grade data.
    -   `POST /api/rankings`: Parses HTML to extract GPA, Class Rank, and Major Rank.
    -   `POST /api/timetable`: Parses and merges course schedule data.

### Frontend (`wxxcx/`)
A **WeChat Mini Program** providing the user interface.

-   **Structure**:
    -   `pages/login/`: Login page with auto-fill and manual CAPTCHA fallback UI.
    -   `pages/schedule/`: Displays the class schedule (Home tab).
    -   `pages/index/`: Displays Grades and Rankings ("成绩" tab).
    -   `utils/config.js`: API configuration (Base URL: `https://hbut.zmj888.asia`).
    -   `utils/util.js`: Utility functions.
-   **Logic Flow**:
    1.  **Login**: Tries auto-login first. If backend returns 429 (OCR failed), prompts user for captcha.
    2.  **Token**: Stores `user_token` to authenticate subsequent requests.
    3.  **Data Display**: Fetches data from backend APIs and renders it.

## Key Files
-   `backend/main.py`: The core backend logic (formerly `cjcx+pm.py`).
-   `backend/requirements.txt`: Python dependencies (pinned `ddddocr==1.4.11` for compatibility).
-   `FC_Deploy_Guide.md`: Instructions for deploying to Alibaba Cloud.
-   `wxxcx/app.json`: Mini Program routing and configuration.
-   `wxxcx/utils/config.js`: Backend URL configuration.
-   `wxxcx/pages/login/login.js`: Frontend login logic handling the auto/manual switching.

## Development Notes
-   **Statelessness**: The backend is completely stateless. The `user_token` contains all necessary session data.
-   **Deployment**: Requires updating `wxxcx/config.js` with the new FC public URL after deployment.
-   **Encryption**: The password encryption logic (`encrypt_password`) mirrors the school's frontend JS encryption.
-   **Target System**: The scraper relies on the HTML structure of `hbut.jw.chaoxing.com`. Changes to the school's system may break the scraper.
