GUILD_ID="$1"
git checkout $GUILD_ID
git add -u
git commit --amend -m "$(date)"
git push --force
