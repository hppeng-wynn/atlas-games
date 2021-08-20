GUILD_ID="$1"
cd atlas-games_store
pwd
git config --global user.name hppeng
git config --global user.email hppeng
git branch $GUILD_ID
git checkout $GUILD_ID
git pull
git push --set-upstream origin $GUILD_ID
