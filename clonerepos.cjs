require('dotenv').config({
    quiet: true,
});

const fs = require('fs')
const { exec } = require('child_process');

const usernames = fs.readFileSync('github-usernames-svaysa.txt', 'utf-8').split('\n').filter(Boolean);

async function main() {
    // loop over usernames and clone their repositories
    for (const username of usernames) {
        const userDir = `./cloned_repos/${username}`;

        // create directory for user if it doesn't exist
        if (!fs.existsSync(userDir)) {
            fs.mkdirSync(userDir, { recursive: true });
        }

        // fetch repositories using GitHub API

        const repos_response = await fetch(`https://api.github.com/users/${username}/repos`, {
            headers: {
                'Authorization': `token ${process.env.GITHUB_TOKEN}`,
                'Accept': 'application/vnd.github.v3+json',
            },
        })
        const repos_data = await repos_response.json()

        if (!repos_response.ok) {
            console.error(`Failed to fetch repositories for ${username}: ${repos_data.message}`);
            continue;
        }

        for (const repo of repos_data) {
            const repoUrl = repo.clone_url;
            const repoName = repo.name;
            const repoDir = `${userDir}/${repoName}`;
            // clone repository

            if (!fs.existsSync(repoDir)) {
                console.log(`Cloning ${repoUrl} into ${repoDir}`);
                exec(`git clone --depth=1 ${repoUrl} ${repoDir}`, (error, stdout, stderr) => {
                    if (error) {
                        console.error(`Error cloning ${repoUrl}: ${error.message}`);
                        return;
                    }
                    if (stderr) {
                        console.error(`stderr: ${stderr}`);
                        return;
                    }
                    console.log("Cloned successfully:", repoUrl);
                });
            } else {
                console.log(`Repository ${repoName} already cloned for user ${username}. Skipping.`);
            }
        };
    }
}

main();