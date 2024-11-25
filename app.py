import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import yagmail
from datasets import load_dataset, Dataset, concatenate_datasets
import http.server
import socketserver

# Load environment variables from .env file
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
HF_TOKEN = os.getenv('HF_TOKEN')
SENDER_EMAIL = os.getenv('SENDER_EMAIL')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD')
HF_REPO_ID = os.getenv('HF_REPO_ID')
RESUME_PATH = os.getenv('RESUME_PATH')

# Conversation stages
HR_EMAIL, JOB_PROFILE, COMPANY_NAME, CITY, ACCESS_ID = range(5)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! I'll help you send your job application email. Let's get started.\n\n"
        "Please enter HR's email address:"
    )
    return HR_EMAIL


async def get_hr_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['hr_email'] = update.message.text
    await update.message.reply_text("Enter the job profile (e.g., Python Developer):")
    return JOB_PROFILE


async def get_job_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['job_profile'] = update.message.text
    await update.message.reply_text("Enter the company name:")
    return COMPANY_NAME


async def get_company_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['company_name'] = update.message.text
    await update.message.reply_text("Enter the city:")
    return CITY


async def get_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['city'] = update.message.text
    await update.message.reply_text("Enter Access ID:")
    return ACCESS_ID


async def get_access_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    access_id = update.message.text
    if access_id != '2003':
        await update.message.reply_text("Invalid Access ID. Try again.")
        return ACCESS_ID

    context.user_data['access_id'] = access_id

    hr_email = context.user_data['hr_email']
    job_profile = context.user_data['job_profile']
    company_name = context.user_data['company_name']
    city = context.user_data['city']

    email_body = f"""
Dear Hiring Manager,

I'm excited to apply for the {job_profile} role at {company_name}. With a strong IT background (B.Tech, CGPA: 7.97) and experience in AI, Machine Learning, and Web Development, I'm confident in my ability to contribute to your team.

Key Highlights:

- AI Intern at VKAPS IT Solutions: Built & deployed AI projects using LangChain Python OpenAI
- Data Science Trainee at Grow Tech: Utilized exploratory data analysis and SQL
- Projects: Online Code Review Tool, Automatic Ticket Classification Tool (details on attached resume)

Tech Skills:

- Programming: Python, SQL
- AI/ML: LangChain, LLMs, Pinecone, Cohere
- Web Dev: Streamlit
Attached: Resume (including full project details, education, and additional experience)

Contact:

- Email: sujal.tamrakar@outlook.com
- Phone: +91-7067599678
- LinkedIn: linkedin.com/in/sujaltamrakar
- GitHub: github.com/sujal03

Best Regards, Sujal Tamrakar
    """

    # Send the email
    try:
        yag = yagmail.SMTP(user=SENDER_EMAIL, password=SENDER_PASSWORD)
        yag.send(to=hr_email, subject=f"Application for {job_profile} at {company_name}", contents=email_body, attachments=RESUME_PATH)

        # Save data to Hugging Face
        new_data = {
            "hr_email": [hr_email],
            "job_profile": [job_profile],
            "company_name": [company_name],
            "company_city": [city]
        }

        existing_dataset = load_dataset(HF_REPO_ID, split="train") if HF_TOKEN else None
        new_dataset = Dataset.from_dict(new_data)

        if existing_dataset:
            updated_dataset = concatenate_datasets([existing_dataset, new_dataset])
        else:
            updated_dataset = new_dataset

        updated_dataset.push_to_hub(HF_REPO_ID)

        await update.message.reply_text("Email sent and data saved successfully!")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operation canceled. Type /start to restart.")
    return ConversationHandler.END


def run_http_server():
    PORT = 8080
    with socketserver.TCPServer(("", PORT), http.server.SimpleHTTPRequestHandler) as httpd:
        print("HTTP server running on port", PORT)
        httpd.serve_forever()

def main():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            HR_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_hr_email)],
            JOB_PROFILE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_job_profile)],
            COMPANY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_company_name)],
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_city)],
            ACCESS_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_access_id)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    import threading
    threading.Thread(target=run_http_server).start()

    application.run_polling()

    print("Bot is running...")
    application.run_polling()


if __name__ == "__main__":
    main()