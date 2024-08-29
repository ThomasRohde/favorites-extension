import logging
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from models import Task, Base

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize SQLAlchemy
engine = create_engine('sqlite:///favorites.db', echo=True)
Session = sessionmaker(bind=engine)
session = Session()

def clean_task_table():
    try:
        # Remove all failed tasks
        failed_tasks = session.query(Task).filter(Task.status == "failed").all()
        for task in failed_tasks:
            session.delete(task)
        logger.info(f"Removed {len(failed_tasks)} failed tasks.")

        # Keep only the most recent "Restart" task
        restart_tasks = session.query(Task).filter(Task.name.like("%Restart%")).order_by(desc(Task.created_at)).all()
        if restart_tasks:
            latest_restart = restart_tasks[0]
            for task in restart_tasks[1:]:
                session.delete(task)
            logger.info(f"Kept the most recent Restart task (ID: {latest_restart.id}) and removed {len(restart_tasks) - 1} older Restart tasks.")
        else:
            logger.info("No Restart tasks found.")

        # Commit the changes
        session.commit()
        logger.info("Task table cleaned successfully.")

    except Exception as e:
        logger.error(f"An error occurred while cleaning the task table: {str(e)}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    logger.info("Starting task table cleanup...")
    clean_task_table()
    logger.info("Task table cleanup completed.")