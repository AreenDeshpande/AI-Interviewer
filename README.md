# AssessAI — AI-Powered Interview Platform

## 🔹 Overview 🔹

**AssessAI** is a cutting-edge platform designed to streamline and automate the technical interview process for recruiters and companies.  
Using **OpenAI’s Large Language Model (LLM)**, **Flask**, **React**, **MongoDB**, and **Twilio**, AssessAI parses candidate resumes, generates tailored interview questions, conducts video interviews, and produces a comprehensive report for recruiters — all with a minimum of human intervention.

---

## 🔹 Features 🔹

✨ **Automated Resume Parsing**   
- Candidate submits their resume.  
- Our **OpenAI LLM parses the resume** to extract key skills, experience, and qualifications.

✨ **Generative Interview Question Bank**   
- The parsed information guides the LLM to generate a set of tailored interview questions.

✨ **Live Video and Audio Interview**   
- Twilio’s video and audio platform sets up a **real-time interview room** for the candidate.

✨ **Transcription and Summary Report**   
- The candidate’s responses are **automatically transcribed**.  
- An **AI-assisted summary report** is generated and sent to recruiters for evaluation.

---

## 🔹 Tech Stack 🔹

- **Frontend**: React
- **Backend**: Flask (Python)
- **Database**: MongoDB
- **AI Model**: OpenAI Large Language Model (ChatCompletion API)
- **Video/Audio Communication**: Twilio
- **Transcription**: Speech-to-text service (integrated through Twilio or another provider)

---

## 🔹 Architectural Flow 🔹

```txt
[ Candidate ]
      |
      ▼ ( Resume )
[ React Frontend ]
      |
      ▼ ( Resume parsed by )
[ Flask + OpenAI ]
      |
      ▼ ( Question Generation )
[ Twilio ]
 ( Audio/Video Call )
      |
      ▼ ( Recording )
[ Transcribe Audio ]
      |
      ▼ ( Summary Report )
[ Report to Recruiter ]
