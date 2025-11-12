require('dotenv').config({
  quiet: true,
})

const axios = require('axios')

const GITHUB_TOKEN = process.env.GITHUB_TOKEN
if (!GITHUB_TOKEN) {
  console.error('Error: GITHUB_TOKEN is not set in environment variables.')
  process.exit(1)
}

const START_DATE = '2025-10-01T00:00:00Z' // October 1, 2025

async function fetchMergeStatus(prApiUrl) {
  try {
    const response = await axios.get(prApiUrl, {
      headers: {
        Accept: 'application/vnd.github.v3+json',
        ...(GITHUB_TOKEN && { Authorization: `token ${GITHUB_TOKEN}` }),
      },
    })
    // The response includes a 'merged' boolean (or you can check merged_at !== null)
    return response.data.merged
  } catch (error) {
    console.error(
      `Error fetching merge status for PR at ${prApiUrl}:`,
      error.message
    )
    // In case of an error, assume the PR was not merged.
    return false
  }
}

async function fetchOwnerDetails(ownerName) {
  try {
    const response = await axios.get(
      `https://api.github.com/users/${ownerName}`,
      {
        headers: {
          Accept: 'application/vnd.github.v3+json',
          ...(GITHUB_TOKEN && { Authorization: `token ${GITHUB_TOKEN}` }),
        },
      }
    )
    return response.data
  } catch (error) {
    console.error(
      `Error fetching details for owner ${ownerName}:`,
      error.message
    )
    return null
  }
}

async function fetchRepositoryDetails(ownerName, repoName) {
  try {
    const response = await axios.get(
      `https://api.github.com/repos/${ownerName}/${repoName}`,
      {
        headers: {
          Accept: 'application/vnd.github.v3+json',
          ...(GITHUB_TOKEN && { Authorization: `token ${GITHUB_TOKEN}` }),
        },
      }
    )
    return response.data
  } catch (error) {
    console.error(
      `Error fetching details for repository ${ownerName}/${repoName}:`,
      error.message
    )
    return null
  }
}

async function fetchUserDetails(username) {
  try {
    const response = await axios.get(
      `https://api.github.com/users/${username}`,
      {
        headers: {
          Accept: 'application/vnd.github.v3+json',
          ...(GITHUB_TOKEN && { Authorization: `token ${GITHUB_TOKEN}` }),
        },
      }
    )
    return response.data
  } catch (error) {
    console.error(`Error fetching details for user ${username}:`, error.message)
    return null
  }
}

async function fetchPRsForUser(username) {
  let prRows = []
  let page = 1
  const per_page = 100 // maximum items per page
  while (true) {
    // Build the search query URL.
    // The query 'author:USERNAME is:pr' returns all pull requests created by USERNAME after the lastUpdated date.
    const searchUrl = `https://api.github.com/search/issues?q=author:${username}+is:pr+created:>=${START_DATE}&per_page=${per_page}&page=${page}`
    console.log(`Fetching PRs for ${username} (page ${page})`)
    try {
      const response = await axios.get(searchUrl, {
        headers: {
          Accept: 'application/vnd.github.v3+json',
          // Include the token if provided
          ...(GITHUB_TOKEN && { Authorization: `token ${GITHUB_TOKEN}` }),
        },
      })

      const data = response.data
      if (!data.items || data.items.length === 0) {
        break // No more results
      }

      // Process each PR item.
      for (const item of data.items) {
        // The API returns a repository URL like: https://api.github.com/repos/owner/repo
        const repoUrl = item.repository_url
        const parts = repoUrl.split('/')
        // Extract the repository owner (organization or user) and repository name.
        const owner = parts[parts.length - 2]
        const repo = parts[parts.length - 1]
        // Extract the PR details.
        const prLink = item.html_url
        const prStatus = item.state // 'open' or 'closed'
        const prDate = item.created_at // Date the PR was created

        // Determine if the PR was merged.
        // The search API returns an object 'pull_request' with a URL for PR details.
        let prMerged = false
        if (item.pull_request && item.pull_request.url) {
          prMerged = await fetchMergeStatus(item.pull_request.url)
        }

        prRows.push({
          github_id: item.id,
          title: item.title,
          body: item.body,
          username, // the author queried
          owner, // repository owner (org or user)
          repo,
          prLink,
          prStatus,
          prMerged,
          prDate,
        })
      }

      // If we received less than the maximum per_page results, we’re done.
      if (data.items.length < per_page) {
        break
      }

      page++
    } catch (error) {
      console.error(`Error fetching PRs for ${username}:`, error.message)
      break
    }
  }
  return prRows
}

module.exports = {
  fetchPRsForUser,
  fetchOwnerDetails,
  fetchUserDetails,
  fetchRepositoryDetails,
  fetchMergeStatus,
}
