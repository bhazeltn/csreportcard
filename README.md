# CS Report Card Generator v2

## Overview

The CS Report Card Generator is a web application designed to automate the creation of Skate Canada CanSkate and custom Pre-CanSkate report cards. It processes raw "Achievements" and "Evaluations" reports from the Uplifter registration system, provides a collaborative workflow for coaches to add comments, and generates final, professional-grade PDF report cards for distribution to skaters.

This project is a complete rebuild of a previous version, designed with a modern, containerized architecture for consistency, scalability, and ease of development.

---

## Core Features

-   **Automated Data Processing**: Intelligently parses complex, multi-sheet Excel reports from Uplifter.
-   **Flexible File Validation**: Automatically identifies report types and validates that session data is consistent between files.
-   **Coach Collaboration Portal**: A secure, "magic link" system allows coaches to add comments and recommendations for their assigned skaters without needing a user account.
-   **Admin Review & Approval**: Provides a central dashboard for an administrator to review, edit, and approve all coach comments before final generation.
-   **Dynamic PDF Generation**:
    -   Fills official, fillable Skate Canada PDF templates for CanSkate reports.
    -   Programmatically generates custom-designed Pre-CanSkate report cards directly from an HTML template.
-   **Containerized Environment**: Uses Docker and Docker Compose for a consistent and isolated development and production environment.

---

## Technology Stack

-   **Backend**: Python with the Flask micro-framework.
-   **Data Processing**: Pandas and Openpyxl for handling Excel files.
-   **PDF Manipulation**: PyMuPDF for PDF generation and filling.
-   **Web Server**: Gunicorn for production, Flask Development Server for development.
-   **Containerization**: Docker & Docker Compose.
-   **Reverse Proxy**: Nginx (for routing traffic on the production server).

---