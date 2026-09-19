import GuildTagManager from './modules/GuildTag.js'; // Update path to match where you saved the class file

const guildTagManager = new GuildTagManager(client);

client.on('userUpdate', async (oldUser, newUser) => {
    for (const [guildId, guild] of client.guilds.cache) {
        if (guild.members.cache.has(newUser.id)) {
            await guildTagManager.handleUserUpdate(oldUser, newUser, guild);
        }
    }
});