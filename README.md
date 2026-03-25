# Event Analytics API

[![Tests](https://github.com/sameelhaider32/event-analytics-api/actions/workflows/tests.yml/badge.svg)](https://github.com/sameelhaider32/event-analytics-api/actions/workflows/tests.yml)

> A small, practical REST API that lets you **log operational events**, **query them later**, and get quick insights like a **summary**, an explainable **health score (0–100)**, and **rule-based alerts**.

---

## ✨ What this project does

This API is useful for anything that produces events: **services, servers, devices, apps**, or any general “asset”.

It supports:

- ✅ Assets & Operators management  
- ✅ Event ingestion (single + bulk)  
- ✅ Event querying with filters (time, severity, type, asset, operator)  
- ✅ Analytics summary (counts, averages, top assets/operators)  
- ✅ Health score (0–100) with breakdown  
- ✅ Alerts (burst, critical severity, unauthorized activity)  
- ✅ Optional Streamlit UI dashboard

---

## 🚀 Quickstart (Windows PowerShell)

### 1) Set up a virtual environment
```powershell
python -m venv venv
.\venv\Scripts\Activate
pip install -r requirements.txt
