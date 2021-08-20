GUILD_ID="$1"
rm -rf atlas-games_store; git clone https://hppeng-wynn:$GITHUB@github.com/hppeng-wynn/atlas-games_store.git;
cd atlas-games_store
git config --global user.name hppeng
git config --global user.email hppeng
git branch $GUILD_ID
git checkout $GUILD_ID
git pull origin $GUILD_ID
git push --set-upstream origin $GUILD_ID --force
