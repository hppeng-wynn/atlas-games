GUILD_ID="$1"
cd atlas-games_store
git add -u
git commit --amend -m "$(date)"
git push --force
