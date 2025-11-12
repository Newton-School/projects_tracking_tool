require('dotenv').config({
  quiet: true,
})

const mongoose = require('mongoose')
const path = require('path')

mongoose
  .connect(process.env.MONGODB_URI)
  .then(() => {
    console.log('Connected to MongoDB')
  })
  .catch((err) => {
    console.error('Error connecting to MongoDB:', err)
  })

const fs = require('fs')

const { User, College } = require('./models')
const { fetchUserDetails } = require('./githubUtils.cjs')
const { fetchPullRequests } = require('./2_fetchPRs.cjs')

const usageExample = `
Usage: node s_import-usernames.cjs <filename> <university>
Example: node s_import-usernames.cjs usernames.txt "Some University"
`

function printUsageAndExit() {
  console.error(usageExample)
  process.exit(1)
}

if (process.argv.length < 4) {
  printUsageAndExit()
}

const FILENAME = process.argv[2]
if (!FILENAME) {
  console.error('Please provide a filename as a command-line argument.')
  printUsageAndExit()
}

const UNIVERSITY = process.argv[3]
if (!UNIVERSITY) {
  console.error('Please provide a university name as a command-line argument.')
  printUsageAndExit()
}

const GITHUB_TOKEN = process.env.GITHUB_TOKEN
if (!GITHUB_TOKEN) {
  console.error('Please set the GITHUB_TOKEN environment variable.')
  printUsageAndExit()
}

const usernames = fs
  .readFileSync(path.join(__dirname, FILENAME), 'utf-8')
  .split('\n')
  .map((line) => line.trim())
  .filter((line) => line.length && !line.startsWith('#'))

const importUsers = async () => {
  const college = await College.findOne({ name: UNIVERSITY }).lean()

  try {
    for (const username of usernames) {
      const existingUser = await User.findOne({ username })
      if (existingUser) {
        console.log(`User ${username} already exists. Skipping.`)

        if (existingUser.college?.toString() !== college._id.toString()) {
          existingUser.college = college._id
          await existingUser.save()
          console.log(`Updated college for user: ${username}`)
        }

        if (existingUser.role !== 'student') {
          existingUser.role = 'student'
          await existingUser.save()
          console.log(`Updated role to student for user: ${username}`)
        }

        if (existingUser.year !== '1st Year') {
          existingUser.year = '1st Year'
          await existingUser.save()
          console.log(`Updated year to 1st Year for user: ${username}`)
        }

        if (existingUser.name === '') {
          const userDetails = await fetchUserDetails(username)
          if (userDetails && userDetails.name) {
            existingUser.name = userDetails.name
            try {
              await existingUser.save()
            } catch (err) {
              console.error(`Error updating name for user ${username}:`, err)
            }
            console.log(`Updated name for user: ${username}`)
          }
        }

        // Fetch PRs for the existing user
        const totalPRsFetched = await fetchPullRequests([existingUser])
        console.log(`Total PRs fetched for ${username}: ${totalPRsFetched}`)

        continue
      }

      const userDetails = await fetchUserDetails(username)
      if (!userDetails) {
        console.log(`User ${username} not found on GitHub. Skipping.`)
        continue
      }

      let newUser
      try {
        newUser = new User({
          github_id: userDetails.id,
          name: userDetails.name,
          type: userDetails.type,
          username,
          college: college._id,
          year: '1st Year',
          role: 'student',
        })
        await newUser.save()
        console.log(`Inserted user: ${username}`)
      } catch (err) {
        console.error(`Error inserting user ${username}:`, err)
        if (err.code === 11000) {
          console.log(`Duplicate entry for user ${username}. Skipping.`)
          // update username if github_id matches
          const existingByGitHubId = await User.findOne({
            github_id: userDetails.id,
          })
          if (existingByGitHubId && existingByGitHubId.username !== username) {
            existingByGitHubId.username = username
            await existingByGitHubId.save()
            newUser = existingByGitHubId
            console.log(
              `Updated username for user with GitHub ID ${userDetails.id} to ${username}`
            )
          }
        }
        continue
      }
      // Fetch PRs for the newly added user
      const totalPRsFetched = await fetchPullRequests([newUser])
      console.log(`Total PRs fetched for ${username}: ${totalPRsFetched}`)
    }
    console.log('Usernames import completed.')
  } catch (err) {
    console.error('Error importing usernames:', err)
  } finally {
    mongoose.connection.close()
  }
}

importUsers()
