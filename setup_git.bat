git config --global user.name "YCL"
git config --global user.email "chang-1125@hotmail.com"

git init                         # Initializes a new Git repo
git add .                        # Stages all files
git commit -m "Initial bot setup"  # Commits your files

git remote add origin https://github.com/itobori3iron/discord-ai-mud-bot
git branch -M main
git push -u origin main


*use ./setup_git.bat to run the setup procedure*