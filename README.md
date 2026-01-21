# 🚛 Supply Chain Optimizer

<div align="center">

![Python](https://img.shields.io/badge/Python-3.14+-blue.svg)
![LangChain](https://img.shields.io/badge/LangChain-0.1.0+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Status](https://img.shields.io/badge/Status-Concept-orange.svg)

**An AI-driven autonomous agentic workflow for global logistics, demand forecasting, and inventory optimization using multi-agent orchestration.**

[Features](#-features) • [Architecture](#-architecture) • [Case Study](#-case-study-details) • [Agent Capabilities](#-agent-capabilities) • [API Reference](#-api-reference)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Case Study Details](#-case-study-details)
- [Features](#-features)
- [Architecture](#-architecture)
- [Technology Stack](#-technology-stack)
- [Agent Capabilities](#-agent-capabilities)
- [Sample Optimization Flow](#-sample-optimization-flow)
- [Implementation Roadmap](#-implementation-roadmap)
- [API Reference](#-api-reference)

---

## 🎯 Overview

The **Supply Chain Optimizer** is an advanced multi-agent system designed to address the complexities of modern global logistics. By leveraging autonomous agents, the system orchestrates demand prediction, warehouse management, and route optimization to create a resilient, self-healing supply chain.

- 📊 **Demand Forecasting**: Predictive analytics for future sales trends.
- 📦 **Inventory Management**: Real-time stock reconciliation and reorder automation.
- 🚚 **Logistics Orchestration**: Dynamic route optimization and carrier selection.
- ⚠️ **Disruption Management**: Autonomous response to port strikes, weather, or supplier delays.

---

## 📚 Case Study Details

| Attribute      | Description                                                                                                                  |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| **Objective**  | Minimize operational costs and stockouts through autonomous multi-agent coordination and data-driven logistics optimization. |
| **Domain**     | Logistics, Manufacturing, Operations, Supply Chain Management                                                                |
| **Skills**     | Multi-Agent Systems, Time-Series Forecasting, Route Optimization, ERP Integration, LangGraph                                 |
| **Complexity** | Advanced                                                                                                                     |
| **Duration**   | 6-8 weeks implementation                                                                                                     |

### Problem Statement

Modern supply chains suffer from:

- **Fragmentation**: Siloed data between warehouses, carriers, and vendors.
- **Latency**: Delayed response to external disruptions (e.g., port congestion).
- **Inefficiency**: Sub-optimal routing and inventory "phantom" stock.
- **Cost**: Human-intensive procurement and logistics planning.

### Solution

This agentic system transforms the supply chain by:

1. **Unifying Data**: Interfacing with various SAP/ERP and IoT data streams.
2. **Autonomous Reasoning**: Agents "decide" the best reorder points and routes.
3. **Resiliency**: Real-time multi-agent "war rooms" to handle disruptions.
4. **Efficiency**: Continuous optimization of warehouse placements and carrier costs.

---

## ✨ Features

### Core Capabilities

| Feature                      | Description                                                    |
| ---------------------------- | -------------------------------------------------------------- |
| 🤖 **MAS Architecture**      | Specialized agents for Forecasting, Inventory, and Logistics   |
| 📈 **Predictive Demand**     | Time-series analysis for accurate stock predictions            |
| 🗺️ **Dynamic Routing**       | Real-time pathfinding based on traffic, weather, and cost      |
| 🔄 **Auto-Procurement**      | Autonomous Purchase Order (PO) creation and vendor negotiation |
| 🛡️ **Disruption Handling**   | Self-healing logic for supply chain breaks                     |
| 🔗 **ERP & IoT Integration** | Bi-directional syncing with systems of record                  |

### Agent Types

1. **Demand Forecasting Agent**: Predicts sales velocity using historical and market data.
2. **Inventory Management Agent**: Monitors ROP (Reorder Point) and Safety Stock.
3. **Logistics & Route Agent**: Optimizes the physical movement of goods.
4. **Vendor Coordination Agent**: Manages supplier relationships and RFQs.
5. **Orchestrator Agent**: Manages the state machine and cross-agent communication.

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        SUPPLY CHAIN OPTIMIZER AGENT                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      ORCHESTRATOR AGENT                          │   │
│  │  • Logistics State Machine                                        │   │
│  │  • Conflict Resolution                                             │   │
│  │  • Global Optimization Logic                                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│                    ┌───────────────┼───────────────┐                    │
│                    │               │               │                    │
│  ┌─────────────────▼──┐  ┌────────▼────────┐  ┌──▼─────────────────┐  │
│  │ FORECASTING AGENT  │  │ INVENTORY AGENT │  │ LOGISTICS AGENT   │  │
│  │                    │  │                 │  │                    │  │
│  │ • Seasonal Trends  │  │ • Stock Levels  │  │ • Route Planning   │  │
│  │ • Market Signals   │  │ • Reorder Points│  │ • Carrier Selection│  │
│  │ • Promo Impact     │  │ • Lead Times    │  │ • Real-time Alerts │  │
│  └────────────────────┘  └─────────────────┘  └────────────────────┘  │
│                                                                          │
│  ┌────────────────────┐  ┌─────────────────┐  ┌────────────────────┐  │
│  │ VENDOR AGENT       │  │ RISK ANALYST    │  │ COMPLIANCE AGENT   │  │
│  │                    │  │ AGENT           │  │                    │  │
│  │ • PO Generation    │  │ • Port Strikes  │  │ • Tariff Tracking  │  │
│  │ • Negotiations     │  │ • Weather Risk  │  │ • Import Laws      │  │
│  │ • Perf Tracking    │  │ • Hedging Logic │  │ • Sustainability   │  │
│  └────────────────────┘  └─────────────────┘  └────────────────────┘  │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                              DATA LAYER                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ ERP Connect  │  │ IoT Stream   │  │ Weather API  │  │ Carrier API│ │
│  │ (SAP/Oracle) │  │ (Sensors)    │  │ (OpenWeather)│  │ (EasyPost) │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Component             | Technology                       |
| --------------------- | -------------------------------- |
| **AI Framework**      | LangChain, LangGraph             |
| **LLM (Open Source)** | **Llama 4 (via Ollama)**         |
| **Vector Store**      | ChromaDB (Open Source)           |
| **Backend**           | FastAPI, Python 3.12+            |
| **Data Processing**   | Pandas, Prophet, NumPy           |
| **Forecasting**       | Facebook Prophet                 |
| **Database**          | SQLite (Dev) / PostgreSQL (Prod) |
| **Containerization**  | Docker, Docker Compose           |

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.12+**
- **Docker & Docker Compose**
- **Ollama** (for local LLM inference)

### Local Setup

1. **Clone the repository**:

   ```bash
   git clone git@github.com:gsaini/supply-chain-optimizer.git
   cd supply-chain-optimizer
   ```

2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**:

   ```bash
   cp .env.example .env
   # Edit .env and set OLLAMA_MODEL=llama4
   ```

4. **Pull the Llama 4 model**:

   ```bash
   ollama pull llama4
   ```

5. **Run the Application**:
   ```bash
   uvicorn src.main:app --reload
   ```

### Running with Docker

```bash
docker-compose up -d
# The API will be available at http://localhost:8000
```

---

---

## 🤖 Agent Capabilities

### 1. Demand Forecasting Agent

- **Historical Analysis**: Processes 3+ years of SKU data for pattern recognition.
- **External Signal Mapping**: correlates demand with weather, holidays, and economic shifts.
- **Confidence Intervals**: Provides Range-based forecasts (P10, P50, P90).

### 2. Inventory Management Agent

- **Dynamic Safety Stock**: Adjusts safety levels based on current lead-time volatility.
- **Warehouse Balancing**: Suggests stock transfers between regional hubs.
- **Deadstock Identification**: Flags slow-moving SKUs for liquidation.

### 3. Logistics & Route Agent

- **Multi-Modal Optimization**: Switches between Air, Sea, and Road based on urgency/cost.
- **Last-Mile Efficiency**: Integrates with local delivery networks for final fulfillment.
- **Load Consolidation**: Groups small shipments to maximize container utilization.

---

## 📊 Sample Optimization Flow

### Scenario: Red Sea Port Congestion Alert

1. **Risk Analyst Agent** detects a news alert regarding port delays.
2. **Orchestrator** triggers a re-planning session.
3. **Logistics Agent** queries carrier APIs for alternative routes (e.g., Cape of Good Hope or Air Freight).
4. **Inventory Agent** checks current stock buffer to see if the delay is critical.
5. **Demand Agent** verifies if high-priority orders are impacted.
6. **Vendor Agent** negotiates early shipments from supplementary suppliers.
7. **Final Decision**: Orchestrator approves a split-shipment (10% Air for urgent stock, 90% Sea rerouted).

---

## 🔧 API Reference

### Endpoints

| Method | Endpoint                     | Description                 |
| ------ | ---------------------------- | --------------------------- |
| `GET`  | `/api/v1/forecast/{sku}`     | Get demand forecast         |
| `GET`  | `/api/v1/inventory/status`   | Get global stock status     |
| `POST` | `/api/v1/logistics/optimize` | Run route optimization      |
| `POST` | `/api/v1/risk/analyze`       | Analyze external threats    |
| `GET`  | `/api/v1/vendors/orders`     | List active purchase orders |

---

## 🧪 Implementation Roadmap

1. **Phase 1: Data Integration** (SAP/ERP connectivity and data cleaning).
2. **Phase 2: Forecasting Engine** (Implementation of the Demand Agent).
3. **Phase 3: Multi-Agent Logic** (LangGraph workflow setup for Inventory and Logistics).
4. **Phase 4: Real-time Feedback** (IoT and External API integrations).
5. **Phase 5: Automated Procurement** (Vendor agent rollout).

---

<div align="center">

**Author: Gopal Saini**
_Part of the AI Agents Case Studies Collection_

</div>
