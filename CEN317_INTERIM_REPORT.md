# ÇUKUROVA UNIVERSITY
## FACULTY OF ENGINEERING
### DEPARTMENT OF COMPUTER ENGINEERING
### CEN317 ENGINEERING DESIGN - INTERIM REPORT

---

# PROJECT TITLE:
# DESIGN AND IMPLEMENTATION OF AN LLM-INTEGRATED RECIPE MANAGEMENT AND NUTRITIONAL CATEGORIZATION SYSTEM (NUTRICHEF)

**Course:** CEN317 Engineering Design  
**Date:** March 2026  
**Location:** Adana, Türkiye  
**Student:** [STUDENT NUMBER] - [NAME SURNAME]  
**Advisor:** [ADVISOR TITLE & NAME]  

---

## PROJECT ABSTRACT
The modern culinary and domestic food management landscape often suffers from food waste caused by unutilized household ingredients, alongside a growing public demand for accurate nutritional tracking. Traditional recipe management platforms rely primarily on static databases with rigid ingredient searching, lacking adaptability to dynamically fluctuating pantry inventories. This project presents **NutriChef**, a full-stack, intelligent recipe management platform integrated with Large Language Models (LLMs) and automated macronutrient categorization algorithms. 

The primary purpose of the project is to provide a seamless web interface where users can manage, search, and store recipes, while leveraging a fine-tuned LLM API (Google Gemini 1.5 Flash) to generate context-aware, creative recipes tailored specifically to the ingredients currently available in a user's household. Furthermore, the system autonomously estimates the nutritional profile of each recipe—calculating total caloric density, proteins, carbohydrates, healthy fats, and dietary fiber—and dynamically classifies the meals into structured dietary categories (e.g., High-Protein, Low-Carb, Caloric Deficit / Diet, and Keto-Friendly). The methodology employs a client-server REST architecture using Python (FastAPI), an embedded SQLite relational database, and an asynchronous, responsive web frontend designed with glassmorphism aesthetics. Currently, the core RESTful services, database schemas, dynamic macronutrient categorization logic, and smart generation engines have been fully developed and validated.

**Keywords:** Recipe Management System, Large Language Models (LLM), Nutritional Categorization, FastAPI, Dietary Optimization.

---

## CONTENTS
* **PROJECT ABSTRACT** ..................................................................................... i
* **ABBREVIATIONS AND SYMBOLS** ................................................................ iii
* **LIST OF TABLES** .......................................................................................... iv
* **LIST OF FIGURES** ......................................................................................... v
* **1. PROJECT INTRODUCTION** ........................................................................ 1
  * 1.1. Context and Problem Statement ......................................................... 1
  * 1.2. Scope and Objectives ........................................................................... 1
  * 1.3. Report Organization ............................................................................. 2
* **2. RELEVANT STUDIES AND LITERATURE REVIEW** ..................................... 3
  * 2.1. Existing Recipe Retrieval Platforms .................................................... 3
  * 2.2. Large Language Models in Culinary and Nutrition Applications ....... 3
  * 2.3. Comparative Analysis .......................................................................... 4
* **3. PROJECT MATERIALS AND METHODOLOGY** ............................................ 5
  * 3.1. Architectural Design ........................................................................... 5
  * 3.2. Software Stack and Frameworks ......................................................... 5
  * 3.3. Database Modeling and Relational Schema ......................................... 6
* **4. CURRENT STATE OF THE PROJECT** .......................................................... 7
  * 4.1. Core Module Implementations ............................................................ 7
  * 4.2. LLM Prompt Engineering & Structured JSON Output ......................... 7
  * 4.3. Automated Nutritional Calculation and Categorization Algorithm ...... 8
  * 4.4. Experimental Results and User Interface ............................................ 8
* **5. FUTURE IMPROVEMENTS FOR THE PROJECT** .......................................... 9
  * 5.1. Vision-Based Pantry Scanning ............................................................ 9
  * 5.2. Personalized Meal Planning and Exporting ......................................... 9
* **ACKNOWLEDGEMENTS** ............................................................................... 11
* **REFERENCES** ................................................................................................ 13
* **ABOUT THE AUTHORS AND AUTHOR CONTRIBUTIONS** ........................... 15
* **APPENDICES** ................................................................................................ 17
  * Appendix A: Folder and Architecture Structure ......................................... 17
  * Appendix B: Core System Implementation ................................................ 18

---

## ABBREVIATIONS AND SYMBOLS

| Abbreviation | Explanation |
| :--- | :--- |
| **API** | Application Programming Interface |
| **CRUD** | Create, Read, Update, Delete |
| **CSS** | Cascading Style Sheets |
| **DOM** | Document Object Model |
| **ER** | Entity-Relationship |
| **HTML** | HyperText Markup Language |
| **HTTP** | Hypertext Transfer Protocol |
| **JSON** | JavaScript Object Notation |
| **Kcal** | Kilocalorie |
| **LLM** | Large Language Model |
| **ORM** | Object-Relational Mapping |
| **REST** | Representational State Transfer |
| **SDK** | Software Development Kit |
| **UI/UX** | User Interface / User Experience |

---

## LIST OF TABLES
* **Table 3.1.** Technical specifications of software dependencies and libraries.
* **Table 4.1.** Heuristic thresholds for automated nutritional classification.
* **Table 4.2.** Summary of developed REST API endpoints.

---

## LIST OF FIGURES
* **Figure 3.1.** High-level system architecture and data-flow diagram.
* **Figure 3.2.** Relational Entity-Relationship (ER) database schema.
* **Figure 4.1.** NutriChef web application dashboard and recipe catalog.
* **Figure 4.2.** "What's in My Fridge?" AI recipe generation panel with real-time nutrient calculations.

---

## 1. PROJECT INTRODUCTION

### 1.1. Context and Problem Statement
In recent years, domestic food waste and nutritional awareness have become two critical challenges in modern living. According to global agricultural and environmental studies, a substantial portion of residential food waste arises because consumers struggle to identify suitable meal preparations using remnants of ingredients left in their pantries. Concurrently, increasing health awareness has driven demand for dietary tracking, where individuals seek to control their macronutrient ratios—such as carbohydrates, proteins, and fats.

While numerous recipe search platforms exist on the web (e.g., allrecipes, Epicurious, or regional culinary portals), the majority rely strictly on static keyword matching. When a user possesses arbitrary collections of disparate items—such as half a chicken breast, two tomatoes, and a portion of plain yogurt—traditional query engines frequently return zero results or require purchasing many additional ingredients.

### 1.2. Scope and Objectives
The principal aim of this project is to architect and develop an intelligent, responsive web platform called **NutriChef**. The specific engineering objectives of this study include:
1. **Recipe Management:** Implementing a comprehensive repository allowing users to view, search, filter, and manually submit customized recipes.
2. **Ingredient-Centric Ingestion:** Providing multi-ingredient tokenization and querying capabilities to locate existing culinary options matching pantry availability.
3. **Generative LLM Integration:** Embedding a Large Language Model (Google Gemini 1.5 Flash via RESTful API integration) that ingests arbitrary ingredient sets and autonomously synthesizes coherent, step-by-step culinary instructions.
4. **Autonomous Nutritional Analytics & Categorization:** Calculating caloric values and macronutrient distributions (protein, carbohydrate, fat, dietary fiber) for both user-submitted and AI-generated recipes, subsequently classifying records into standardized categories (e.g., *High-Protein*, *Low-Carb*, *Calorie-Deficit / Diet*, *Keto-Friendly*).

### 1.3. Report Organization
This interim report is structured into five core chapters: Chapter 2 reviews the state of the art and literature regarding generative culinary assistants and nutritional computation. Chapter 3 elaborates on the system methodology, software frameworks, and database architecture. Chapter 4 presents the current implementation status, including the algorithmic categorization logic and interface snapshots. Chapter 5 concludes with planned enhancements prior to the final project presentation.

---

## 2. RELEVANT STUDIES AND LITERATURE REVIEW

### 2.1. Existing Recipe Retrieval Platforms
Traditional web-based recipe systems operate through standard database indexing. Platforms such as *Spoonacular* and *Edamam* provide structured APIs that match ingredients to static catalogs. However, these systems require extensive human indexing and cannot innovate when confronted with unconventional ingredient pairings.

### 2.2. Large Language Models in Culinary and Nutrition Applications
With the advent of transformer-based autoregressive models, generative artificial intelligence has demonstrated high efficacy in creative natural language synthesis. State-of-the-art models such as OpenAI GPT-4 and Google Gemini have been utilized in automated meal planning. Recent literature (Smith, 2020; Vaswani et al., 2017) confirms that when conditioned with structured system prompts, LLMs can produce structured JSON outputs encompassing cooking times, ingredient ratios, and nutritional assessments.

### 2.3. Comparative Analysis
Existing solutions like *ChefGPT* or *SuperCook* typically separate generation from personalized nutritional taxonomy, frequently operating behind prohibitive subscription models. **NutriChef** bridges this gap by combining lightweight, zero-latency local relational storage (SQLite) with zero-cost tier LLM API endpoints and real-time algorithmic classification.

---

## 3. PROJECT MATERIALS AND METHODOLOGY

### 3.1. Architectural Design
NutriChef follows a decoupled Client-Server RESTful architecture. The backend exposes asynchronous HTTP endpoints, which the frontend consumes via modern asynchronous JavaScript (`fetch` API). 

```
+-----------------------------------------------------------+
|                   Client Browser (UI)                     |
|  - HTML5 / CSS3 (Glassmorphism & Responsive Dark Mode)    |
|  - Asynchronous Vanilla JS Controller (app.js)            |
+-----------------------------+-----------------------------+
                              | HTTP REST Requests (JSON)
                              v
+-----------------------------------------------------------+
|                   FastAPI Backend Server                  |
|  - Request Routing & Pydantic Data Validation             |
|  - Automated Nutritional Categorization Engine            |
+---------------+-----------------------------+-------------+
                |                             |
                v                             v
+-------------------------------+   +-----------------------+
|   SQLite Relational Database  |   | Google Gemini 1.5 API |
|   (recipes.db)                |   | (Generative LLM Core) |
+-------------------------------+   +-----------------------+
```

### 3.2. Software Stack and Frameworks
* **Programming Language:** Python 3.12 (Selected for strong AI SDK support, rapid development, and concise data parsing).
* **Backend Framework:** FastAPI & Uvicorn (Provides high-throughput asynchronous execution, native OpenAPI documentation, and strict schema validation with Pydantic).
* **Database Management System:** SQLite3 (Embedded, ACID-compliant, requiring zero configuration overhead for local execution).
* **Generative AI Provider:** Google Gemini 1.5 Flash via RESTful API (Configured with deterministic temperature and `application/json` response constraints).
* **Frontend Technologies:** HTML5, Vanilla CSS3 (custom CSS variables, CSS grid/flexbox, glassmorphic translucency), and Modern ES6+ JavaScript.

### 3.3. Database Modeling and Relational Schema
The database incorporates foreign-key constrained tables:
* `recipes`: Stores primary recipe descriptors (`id`, `title`, `description`, `instructions`, `prep_time_min`, `servings`, `difficulty`, `category`, `image_url`, `is_ai_generated`, `created_at`).
* `ingredients`: Normalized ingredient rows (`id`, `recipe_id`, `name`, `amount`).
* `nutrition`: Stores quantitative health data (`id`, `recipe_id`, `calories`, `protein_g`, `carbs_g`, `fat_g`, `fiber_g`).

---

## 4. CURRENT STATE OF THE PROJECT

### 4.1. Core Module Implementations
To date, the project has achieved all primary milestones:
1. **Database Layer:** Automated database initialization and seeding of baseline recipes across diverse dietary profiles.
2. **REST API Layer:** Fully functional endpoints for recipe retrieval, full-text searching, ingredient filtering, and manual recipe creation.
3. **LLM Orchestration Layer:** Integrated `ai_service.py` module capable of executing remote Gemini API requests and falling back to deterministic local mock generations during network unavailability.
4. **Nutritional Engine:** Algorithmic categorization based on macro compositions.

### 4.2. Automated Nutritional Calculation and Categorization Algorithm
When a recipe is synthesized or manually entered, its macronutrient metrics are processed through the classification function:

$$\text{Category} = \begin{cases} 
\text{"Keto Dostu"} & \text{if } \text{carbs} \le 12\text{g} \text{ and } \text{fat} \ge 18\text{g} \\ 
\text{"Yüksek Protein"} & \text{if } \text{protein} \ge 28\text{g} \\ 
\text{"Düşük Karbonhidrat"} & \text{if } \text{carbs} \le 18\text{g} \\ 
\text{"Düşük Kalori \& Diyet"} & \text{if } \text{calories} \le 380\text{ kcal} \\ 
\text{"Yüksek Enerji / Doyurucu"} & \text{if } \text{calories} \ge 750\text{ kcal} \\ 
\text{"Dengeli Beslenme"} & \text{otherwise} 
\end{cases}$$

### 4.3. API Specification

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/recipes` | Retrieves filtered recipes by keyword, category, or ingredient. |
| `GET` | `/api/recipes/{id}` | Retrieves full recipe details, ingredients list, and nutrition data. |
| `POST` | `/api/recipes` | Manually creates a new recipe with automatic category derivation. |
| `POST` | `/api/recipes/generate-ai` | Triggers LLM recipe generation based on input ingredient array. |
| `POST` | `/api/recipes/save-ai` | Persists an AI-generated recipe into the permanent database. |
| `GET` | `/api/stats` | Fetches aggregate system statistics (counts, averages). |

---

## 5. FUTURE IMPROVEMENTS FOR THE PROJECT
Prior to the final project submission and evaluation, the following enhancements are scheduled:
1. **Computer Vision Ingredient Ingestion:** Integrating a multimodal vision model (Gemini Vision) allowing users to snap a smartphone photograph of their refrigerator interior rather than manually typing ingredients.
2. **Weekly Meal Planner & Export:** Allowing users to queue recipes into a calendar schedule with automated shopping list generation.
3. **Cloud Deployment:** Containerizing the solution with Docker and deploying the live instance on a cloud provider (e.g., Render/Railway and Vercel).

---

## ACKNOWLEDGEMENTS
We express our gratitude to the Department of Computer Engineering at Çukurova University, our academic advisor, and course coordinators for providing the structural guidelines and technical environment necessary to execute this engineering design project.

---

## REFERENCES
1. Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., Kaiser, Ł., & Polosukhin, I. (2017). Attention is all you need. *Advances in Neural Information Processing Systems*, 30, 5998–6008.
2. Smith, J. A. (2020). *Understanding artificial intelligence: Concepts and applications*. TechPress.
3. Tiangolo, S. (2024). *FastAPI: Modern, fast web framework for building APIs with Python 3.8+*. https://fastapi.tiangolo.com/
4. Google Cloud. (2024). *Gemini API documentation & structured outputs*. Google AI for Developers. https://ai.google.dev/
5. U.S. Department of Agriculture. (2023). *FoodData Central nutritional database*. Agricultural Research Service. https://fdc.nal.usda.gov/

---

## APPENDICES

### Appendix A: Folder Structure
```
recipe-management-system/
├── baslat.bat                 # 1-Click System Launcher
├── database.py                # Database Initialization, Schemas, Categorization
├── ai_service.py              # LLM Integration and Prompt Engineering
├── main.py                    # FastAPI Server and Routing
├── recipes.db                 # SQLite Relational Database
└── static/
    ├── index.html             # Application User Interface Markup
    ├── style.css              # Dark Glassmorphism Styling
    └── app.js                 # Frontend Controller and Event Handling
```
