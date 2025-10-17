Leado.ai — Smart Contact Form Automation

Automate bulk contact form submissions with AI-crafted personalized messages

🚀 Overview

Leado.ai (formerly FormAI Bot) is an intelligent automation tool designed to streamline lead generation and outreach.
It automatically detects contact forms on websites, fills them with AI-generated personalized messages, and submits them — all without manual intervention.

Built with Python, Selenium, and OpenAI API, the tool allows users to process multiple URLs in bulk, making it ideal for businesses and agencies looking to optimize their contact workflows.

🧠 Key Features

🔍 Automated Contact Form Detection — Scans websites and identifies contact pages dynamically.

📝 AI-Powered Form Filling — Uses OpenAI API to generate human-like, personalized messages for each submission.

⚙️ Bulk Automation — Supports batch processing of multiple URLs to maximize efficiency.

🌐 Smart Error Handling — Handles form variations, captchas, and failed submissions intelligently.

📊 Real-Time Logging — Provides detailed console logs and success reports for every automation run.

🧰 Tech Stack

Programming Language: Python

Frameworks & Libraries: Selenium, Flask (optional UI), Requests, BeautifulSoup

AI Integration: OpenAI API

Frontend (Optional): HTML, CSS (for dashboard templates)

🏗️ Project Structure
formaibot/
│
├── formbot/                 # Core automation logic
├── templates/               # HTML templates for dashboard/UI
├── static/                  # Static assets (CSS, JS, images)
├── app.py                   # Main Flask app entry point
├── aiseo.py                 # AI message generation logic
├── pitchbot-key.pem         # API key or certificate file
├── testingserver.pem        # SSL certificate for testing
└── requirements.txt         # Python dependencies

⚙️ Installation & Setup

Clone the repository:

git clone https://github.com/<your-username>/formaibot.git
cd formaibot


Install dependencies:

pip install -r requirements.txt


Set up environment variables:
Create a .env file and add your OpenAI API key and other configurations.

OPENAI_API_KEY=your_openai_key_here


Run the bot:

python app.py

🧩 Usage

Input a list of target URLs.

The bot automatically identifies contact forms and fills them using AI-generated personalized content.

Logs every action and generates a report of successful submissions.

💡 Example Use Cases

Automating outreach for digital marketing agencies.

Lead generation for SaaS or service-based businesses.

Testing and validating contact forms across multiple client websites.

🤝 Contributing

Contributions are welcome!
If you’d like to improve the project, please fork the repo, make your changes, and submit a pull request.

🧾 License

This project is licensed under the MIT License – feel free to use, modify, and distribute it.

👨‍💻 Author

Amarjeet Kumar
Software Developer Intern at MindAptix
📧 ak7462514@gmail.com
🔗 GitHub: AmarjeetJyotis
