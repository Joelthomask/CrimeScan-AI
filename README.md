# CrimeScan AI
<p align="center">
  <img src="Assets\logo.png" alt="logo" width="220"/>
</p>
<h3 align="center">AI‑Powered Criminal Face Detection & Recognition System</h3>


------------------------------------------------------------------------

## 🌐 Project Overview

**CrimeScan AI** is an intelligent forensic investigation system
designed to automatically detect, enhance, and recognize faces from
**CCTV footage, live webcam feeds, and uploaded images**.

The system addresses real‑world surveillance challenges such as:

-   Low resolution footage
-   Motion blur
-   Poor lighting conditions
-   Noise and compression artifacts
-   Masked or occluded faces
-   Pose variations

CrimeScan improves image quality using an intelligent enhancement
pipeline before performing recognition and matching against a criminal
database.

A desktop application enables investigators to perform recognition,
enroll suspects, analyze results, and manage records efficiently.

The system also learns from previous results to continuously improve
performance.

------------------------------------------------------------------------

## 🎯 Project Objectives

-   Detect and recognize faces from images and video feeds.
-   Automatically assess image quality before recognition.
-   Enhance low‑quality images using AI‑based enhancement modules.
-   Preserve forensic identity using enhancement validation.
-   Maintain accurate criminal identity database.
-   Support real‑time and offline recognition workflows.
-   Continuously improve enhancement policies using adaptive learning.

------------------------------------------------------------------------

## 🧠 Key System Features

### Face Processing

-   Multi‑face detection
-   Mask‑aware recognition
-   Embedding‑based identity matching
-   Unknown person detection

### Intelligent Enhancement

Automatic enhancement modules:

-   Deblurring
-   Denoising
-   Brightness & contrast correction
-   Super‑resolution restoration
-   Pose normalization
-   Mask handling

### Quality Assessment

Detects:

-   Blur
-   Noise
-   Resolution issues
-   Lighting problems
-   Pose deviations

### GUI & Database

-   Criminal enrollment system
-   Database record management
-   Live webcam recognition
-   Investigation workflow support

------------------------------------------------------------------------

## ⚙️ System Architecture Flow

    Input Image / CCTV / Webcam
                ↓
    Quality Assessment
                ↓
    Intelligence Engine
                ↓
    Enhancement Block
                ↓
    Forensic Guard Validation
                ↓
    Face Detection
                ↓
    Embedding Extraction
                ↓
    Face Vector Matching
                ↓
    Database Result
                ↓
    Adaptive Learning Update

------------------------------------------------------------------------

## 📂 System Pipelines

### 1. CrimeScan Investigation Mode

Used for suspect identification.

Flow: Input → Quality Check → Enhancement → Guard Validation →
Recognition → Database Match → Output

------------------------------------------------------------------------

### 2. Live Webcam / CCTV Mode

Real‑time recognition pipeline.

Flow: Camera → Frame Sampling → Detection → Embedding → Matching → Live
Display

Enhancement is minimized for speed.

------------------------------------------------------------------------

### 3. Enrollment Mode

Adds individuals to database.

Flow: Upload → Face Detection → Preprocessing → Embedding Extraction →
Database Storage

Only high‑quality images accepted.

------------------------------------------------------------------------

### 4. Image Improver Mode

Enhancement only.

Flow: Input → AutoEnhancer → Save Enhanced Image

No recognition performed.

------------------------------------------------------------------------

## 🧩 Core Modules

### AutoEnhancer System

Responsible for improving image quality.

Components: - Quality Assessment - Intelligence Engine - Enhancement
Block - Forensic Guard - Adaptive Learner

### Face Recognition Engine

Responsible for identity matching.

Components: - Face Detection - Mask Handling - Embedding Extraction -
Vector Matching

### Database System

Stores: - Criminal records - Embeddings - Recognition logs

------------------------------------------------------------------------

## 🤖 Models Used

### Face Detection & Recognition

-   RetinaFace
-   ArcFace

### Enhancement Models

-   GFPGAN -- Face restoration & super‑resolution
-   HiDiff -- Deblurring
-   NLM -- Denoising
-   CLAHE -- Brightness correction
-   FAN -- Pose checking

### Quality Assessment

-   CLIP‑IQA
-   Pose analysis algorithms

### Matching Algorithm

-   Cosine similarity

------------------------------------------------------------------------


## 🚀 Installation & Setup

### Clone Repository

``` bash
git clone https://github.com/Joelthomask/CrimeScan-AI.git
cd CrimeScan-AI
```

### Create Environment

``` bash
python -m venv venv
venv\Scripts\activate
```

### Install Dependencies

``` bash
pip install -r requirements.txt
```

------------------------------------------------------------------------

## 📦 External Model Downloads

Due to size limitations, some models are hosted externally.

### HI‑Diff Experiments

Place inside:

    auto_enhancer/enhancement/deblurring/HI_Diff/experiments/

[![Download from GDrive](https://img.shields.io/badge/Download-GDrive-blue?style=for-the-badge&logo=google-drive)](https://drive.google.com/open?id=1lG4UsQmKRDBKjorQ6mgffS2Wi8SSec8J&usp=drive_fs)


------------------------------------------------------------------------

### GFPGAN Weights

Place inside:

    auto_enhancer/enhancement/resolution/GFPGAN/gfpgan/weights/

[![Download from GDrive](https://img.shields.io/badge/Download-GDrive-blue?style=for-the-badge&logo=google-drive)](https://drive.google.com/open?id=1FTZjwODN0uWuxoTCZ_uaT3SEFM8pd25N&usp=drive_fs)


------------------------------------------------------------------------

### RetinaFace Weights

Place inside:

    face_recognition/detection/retinaface/weights/

[![Download from GDrive](https://img.shields.io/badge/Download-GDrive-blue?style=for-the-badge&logo=google-drive)](https://drive.google.com/open?id=1T-XSP1638go15tNjLwqVvV7jeer_2wrJ&usp=drive_fs)


------------------------------------------------------------------------

### InsightFace Buffalo_L Models

Place inside:

    face_recognition/embedding/InsightFace/models/buffalo_l/


[![Download from GDrive](https://img.shields.io/badge/Download-GDrive-blue?style=for-the-badge&logo=google-drive)](https://drive.google.com/open?id=188oKV4aXZSzyzarQn9zHbjDISDYrOx_u&usp=drive_fs)


------------------------------------------------------------------------
---

## 🖥 Desktop Application Build & Installer

CrimeScan AI is also packaged as a **standalone Windows desktop application**, allowing investigators to run the system without manually setting up Python environments.

---

### 📦 Prebuilt Installer (Recommended for End Users)

A ready-to-use installer is available for quick setup.

The installer automatically installs the CrimeScan desktop application with all required runtime components.

[![Download Installer](https://img.shields.io/badge/Download-Desktop%20Installer-blue?style=for-the-badge&logo=windows)](https://drive.google.com/open?id=1wYVAlRqFKhPZ7ewDb9_kJlOHPiwnOxC_&usp=drive_fs)

After installation:
- Launch CrimeScan from the desktop or start menu.
- Models should still be placed in required folders as described above.

---

### 🚀 launcher.py

Located in the project root:


Purpose:
- Serves as the **runtime launcher** for the packaged application.
- Ensures correct environment initialization.
- Handles safe startup of the CrimeScan pipeline.
- Used in packaged builds to reliably start the application.

The launcher acts as a stable entry point when running the packaged executable.

---

### ⚙️ Inno Setup Installer Script

script.iss

The project includes an installer configuration script:


Purpose:
- Used with **Inno Setup** to create the Windows installer.
- Packages executable, assets, and runtime files.
- Creates shortcuts and installation directories.
- Enables distribution of CrimeScan as a professional desktop application.

Developers can modify this script to generate updated installers.

---

### 📌 Recommended Usage

For developers:

------------------------------------------------------------------------
## ✅ Current System Status

✔ Recognition pipeline operational\
✔ Enhancement modules integrated\
✔ GUI fully functional\
✔ Database enrollment working\
✔ Real‑time recognition supported

------------------------------------------------------------------------

## 🔮 Future Improvements

-   Distributed recognition support
-   Cloud database synchronization
-   Edge device deployment
-   Automatic model downloader
-   Performance optimization
------------------------------------------------------------------------


## 📚 Project Documentation & Knowledge Support

Comprehensive project resources are available for learners, researchers, and developers who wish to understand or build upon the CrimeScan AI system.

Available materials include:

- Complete project PPT presentation
- System architecture explanation
- Pipeline flow documentation
- Module-wise implementation details
- Folder structure explanation
- Deployment and packaging workflow
- Enhancement and recognition methodology
- Technical defense and presentation guidance

These materials provide deeper understanding of system design, implementation decisions, and investigation workflows.

For access to project documentation or technical guidance regarding CrimeScan AI, please contact the author.

📧 Contact: **Joel Thomas**  
- 📧 Email: joel16005@gmail.com  
- 🔗 [LinkedIn](https://www.linkedin.com/in/joel-thomask)  
---

------------------------------------------------------------------------

## 👥 Project Team

**SCMS School of Engineering and Technology**\
Department of Computer Science & Engineering

Team Members: - Joel Thomas - Jinto Raj - Cukoo Biji - Gokul K Reghu


------------------------------------------------------------------------

## 👤 Author & Repository

**👨‍💻 Joel Thomas**  
- 🔗 [LinkedIn](https://www.linkedin.com/in/joel-thomask)  
- 💻 [GitHub](https://github.com/Joelthomask)  
- 📧 Email: joel16005@gmail.com  


------------------------------------------------------------------------

---

## 🧾 License & Acknowledgements

- Licensed under the **MIT License**.
- Based on the open-source **RetinaFace** project.
- Datasets used: **RMFD**, **MAFA**, **CMFD**, **Custom Surveillance Dataset**.
- All the images and datasets and models used here belongs to the respective owners.
- All the logos and Vedios belongs to the respective owners.
- MIT © [Joel Thomas](LICENSE.txt)
---
## Code of Conduct

You can find our Code of Conduct [here](CODE_OF_CONDUCT.md).

------------------------------------------------------------------------
## ⭐ Contribute

Pull requests and issues are welcome.  
You can contribute by improving dataset balance scripts, fine-tuning on other backbones, or optimizing for embedded systems.

---

<p align="center">
  <em>“Built with purpose — precision and performance for real-world recognition.”</em>
</p>
