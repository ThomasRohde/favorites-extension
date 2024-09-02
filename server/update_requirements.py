import subprocess
import sys

def update_requirements():
    try:
        # Ensure pip is up to date
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=True)
        
        # Install pipreqs if not already installed
        subprocess.run([sys.executable, "-m", "pip", "install", "pipreqs"], check=True)
        
        # Use pipreqs to generate requirements.txt
        subprocess.run(["pipreqs", ".", "--force"], check=True)
        
        print("requirements.txt has been updated successfully.")
        
        # Display the contents of the updated requirements.txt
        with open("requirements.txt", "r") as f:
            print("\nUpdated requirements.txt contents:")
            print(f.read())
    
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    update_requirements()