GUILD_ID="$1"
cd atlas-games_store
git config --global user.name hppeng
git config --global user.email hppeng
git branch $GUILD_ID
git checkout $GUILD_ID
touch a
git add a
git commit -m "$(date)"
git push --set-upstream origin $GUILD_ID
