const mongoose = require('mongoose')

const schemas = {
  User: new mongoose.Schema(
    {
      username: {
        type: String,
        unique: true,
        required: true,
      },
      github_id: {
        type: Number,
        unique: true,
        required: true,
      },
      full_name: {
        type: String,
        default: '',
      },
      college: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'College',
        default: null,
      },
      year: {
        type: String,
        enum: ['1st Year', '2nd Year', '3rd Year', '4th Year'],
        default: null,
      },
      role: {
        type: String,
        enum: ['student', 'instructor', 'admin'],
        default: 'student',
      },
    },
    {
      timestamps: true,
    }
  ),

  College: new mongoose.Schema(
    {
      name: {
        type: String,
        unique: true,
        required: true,
      },
    },
    {
      timestamps: true,
    }
  ),

  GitHubOwner: new mongoose.Schema(
    {
      github_id: {
        type: Number,
        unique: true,
        required: true,
      },
      name: {
        type: String,
      },
      username: {
        type: String,
        unique: true,
        required: true,
      },
      type: {
        type: String,
        enum: ['User', 'Organization'],
        required: true,
        default: 'User',
      },
    },
    {
      timestamps: true,
    }
  ),

  GitHubRepository: new mongoose.Schema(
    {
      github_id: {
        type: Number,
        unique: true,
        required: true,
      },
      name: {
        type: String,
        required: true,
      },
      owner: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'GitHubOwner',
      },
      is_gosc: {
        type: Boolean,
        default: false,
      },
      is_redFlagged: {
        type: Boolean,
        default: false,
      },
    },
    {
      timestamps: true,
    }
  ),

  GitHubPR: new mongoose.Schema(
    {
      github_id: {
        type: Number,
        unique: true,
        required: true,
      },
      title: {
        type: String,
        default: '',
      },
      body: {
        type: String,
        default: '',
      },
      author: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'User',
      },
      repository: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'GitHubRepository',
      },
      link: {
        type: String,
        default: '',
        unique: true,
        required: true,
      },
      is_open: {
        type: Boolean,
        default: true,
      },
      is_merged: {
        type: Boolean,
        default: false,
      },
      is_redFlagged: {
        type: Boolean,
        default: false,
      },
      redFlag_reason: {
        type: String,
        default: '',
      },
      redFlag_by: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'User',
        default: null,
      },
      redFlag_at: {
        type: Date,
        default: null,
      },
    },
    {
      timestamps: true,
    }
  ),
}

const models = {}

for (const [name, schema] of Object.entries(schemas)) {
  models[name] = mongoose.model(name, schema)
}
module.exports = models
