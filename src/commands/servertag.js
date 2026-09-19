const GuildTag = require('./modules/GuildTag');
const guildTagManager = new GuildTag(client);

// Attach the database connection to the client if not already done
// client.cxn = yourDatabasePool;

client.on('userUpdate', async (oldUser, newUser) => {
    // Loop through all guilds the bot shares with the user
    for (const [guildId, guild] of client.guilds.cache) {
        if (guild.members.cache.has(newUser.id)) {
            await guildTagManager.handleUserUpdate(oldUser, newUser, guild);
        }
    }
});