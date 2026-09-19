const { 
    Client, 
    GatewayIntentBits, 
    PermissionFlagsBits, 
    EmbedBuilder, 
    ActionRowBuilder, 
    ButtonBuilder, 
    SlashCommandBuilder,
    ChannelType
} = require('discord.js');

class GuildTag {
    constructor(client) {
        this.client = client;
    }

    async getGuildTagConfig(guildId) {
        const query = `
            SELECT enabled, channel_id, message, roles
            FROM guild_tags
            WHERE server_id = $1
        `;
        const result = await this.client.cxn.query(query, [guildId]);
        const record = result.rows[0];
        if (record) {
            return {
                enabled: record.enabled,
                channel_id: record.channel_id,
                message: record.message,
                roles: record.roles || []
            };
        }
        return null;
    }

    async getGuildTagUsers(guildId) {
        const query = `
            SELECT user_id, adopted_at
            FROM guild_tag_users
            WHERE server_id = $1
            ORDER BY adopted_at DESC
        `;
        const result = await this.client.cxn.query(query, [guildId]);
        return result.rows;
    }

    // --- Core Event Listeners ---

    async handleUserUpdate(beforeUser, afterUser, guild) {
        const member = await guild.members.fetch(afterUser.id).catch(() => null);
        if (!member) return;

        const config = await this.getGuildTagConfig(guild.id);
        if (!config || !config.enabled) return;

        // Note: adjust property checks according to your specific Discord.js version support for clan/primary_guild tags
        const beforePrimary = beforeUser.primaryGuild || beforeUser.clan || null;
        const afterPrimary = afterUser.primaryGuild || afterUser.clan || null;

        const beforeId = beforePrimary?.id || null;
        const afterId = afterPrimary?.id || null;
        const beforeEnabled = beforePrimary?.identityEnabled || false;
        const afterEnabled = afterPrimary?.identityEnabled || false;

        if (beforeId === afterId && beforeEnabled === afterEnabled) return;

        const wasMatch = beforeEnabled && beforeId && guild.id === String(beforeId);
        const isMatch = afterEnabled && afterId && guild.id === String(afterId);

        if (isMatch && !wasMatch) {
            const checkQuery = "SELECT 1 FROM guild_tag_users WHERE server_id = $1 AND user_id = $2";
            const checkResult = await this.client.cxn.query(checkQuery, [guild.id, member.id]);
            const alreadyTracked = checkResult.rows.length > 0;

            const insertQuery = `
                INSERT INTO guild_tag_users (server_id, user_id)
                VALUES ($1, $2)
                ON CONFLICT (server_id, user_id) DO NOTHING
            `;
            await this.client.cxn.query(insertQuery, [guild.id, member.id]);

            if (config.roles && config.roles.length > 0) {
                const botMember = guild.members.me;
                const rolesToAdd = config.roles
                    .map(rid => guild.roles.cache.get(rid))
                    .filter(role => role && !member.roles.cache.has(role.id) && role.position < botMember.roles.highest.position);

                if (rolesToAdd.length > 0) {
                    try {
                        await member.roles.add(rolesToAdd, "User adopted guild tag");
                    } catch (err) {
                        // Handle error silently or log
                    }
                }
            }

            if (!alreadyTracked && config.channel_id && config.message) {
                const channel = guild.channels.cache.get(config.channel_id);
                if (channel) {
                    try {
                        let message = config.message
                            .replace(/{user\.mention}/g, `<@${member.id}>`)
                            .replace(/{user\.name}/g, member.user.username)
                            .replace(/{user\.id}/g, member.id)
                            .replace(/{server\.name}/g, guild.name);

                        await channel.send({
                            content: message,
                            allowedMentions: { users: [member.id] }
                        });
                    } catch (err) {
                        // Handle error
                    }
                }
            }
        } else if (wasMatch && !isMatch) {
            const deleteQuery = "DELETE FROM guild_tag_users WHERE server_id = $1 AND user_id = $2";
            await this.client.cxn.query(deleteQuery, [guild.id, member.id]);

            if (config.roles && config.roles.length > 0) {
                const botMember = guild.members.me;
                const rolesToRemove = config.roles
                    .map(rid => guild.roles.cache.get(rid))
                    .filter(role => role && member.roles.cache.has(role.id) && role.position < botMember.roles.highest.position);

                if (rolesToRemove.length > 0) {
                    try {
                        await member.roles.remove(rolesToRemove, "User removed guild tag");
                    } catch (err) {
                        // Handle error
                    }
                }
            }
        }
    }
}

module.exports = GuildTag;