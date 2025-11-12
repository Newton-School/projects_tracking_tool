require('dotenv').config({
  quiet: true,
})

const mongoose = require('mongoose')

mongoose
  .connect(process.env.MONGODB_URI)
  .then(() => {
    console.log('Connected to MongoDB')
  })
  .catch((err) => {
    console.error('Error connecting to MongoDB:', err)
  })

const fs = require('fs')

const {
  User,
  College,
  GitHubOwner,
  GitHubRepository,
  GitHubPR,
} = require('./models')

// const USERS_FILE = '/Users/krushn/Studio/gitgopr-supa-mod/users.json'

// const users = JSON.parse(fs.readFileSync(USERS_FILE, 'utf-8'))
const colleges = ['NST ADYPU', 'NST RU', 'NST SVYASA']

const insertedColleges = []

const setupDatabase = async () => {
  try {
    // Clear existing data
    await User.deleteMany({})
    await College.deleteMany({})
    await GitHubOwner.deleteMany({})
    await GitHubRepository.deleteMany({})
    await GitHubPR.deleteMany({})
    console.log('Cleared existing data')

    // Insert colleges
    const collegeDocs = await College.insertMany(
      colleges.map((name) => ({ name }))
    )
    insertedColleges.push(...collegeDocs)
    console.log('Colleges inserted/updated')

    // // Insert users
    // for (const userData of users) {
    //   if (!userData.username || !userData.github_id) {
    //     console.warn(
    //       `Skipping user with missing username or github_id: ${JSON.stringify(
    //         userData
    //       )}`
    //     )
    //     continue
    //   }

    //   let college = null

    //   if (userData.college) {
    //     college = insertedColleges.find((c) => c.name === userData.college)

    //     if (!college) {
    //       console.warn(
    //         `College not found for user ${userData.username}: ${userData.college}, Creating...`
    //       )
    //       college = new College({ name: userData.college })
    //       await college.save()
    //       insertedColleges.push(college)
    //       console.log(`Inserted new college: ${college.name}`)
    //     }
    //   }

    //   const user = new User({
    //     username: userData.username,
    //     github_id: userData.github_id,
    //     full_name: userData.full_name || '',
    //     college: college ? college._id : null,
    //     year: userData.year
    //       ? ['1st Year', '2nd Year', '3rd Year', '4th Year'].includes(
    //           userData.year
    //         )
    //         ? userData.year
    //         : null
    //       : null,
    //     role: userData.role?.toLowerCase() || 'student',
    //   })

    //   await user.save()
    //   console.log(`Inserted/Updated user: ${user.username}`)
    // }
    // console.log('Users inserted/updated')
  } catch (err) {
    console.error('Error setting up database:', err)
  } finally {
    mongoose.connection.close()
  }
}


setupDatabase()
