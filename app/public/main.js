const { createApp, ref, computed, onMounted } = Vue

createApp({
  setup() {

    onMounted(() => {
      M.AutoInit()
    })

    const users = ref([])
    const colleges = ref([])
    const owners = ref([])
    const repositories = ref([])
    const prs = ref([])
    const allPRs = ref([]) // Store all PRs for filtering

    const statistics = ref(null)
    
    // Search-related state
    const searchQuery = ref('')
    const searchResults = ref([])
    const showSearchResults = ref(false)
    const selectedUser = ref(null)
    const userProfileStats = ref(null)
    
    let searchTimeout = null

    function fetchData() {
      fetch('/api/GitHubPRs')
        .then((response) => response.json())
        .then((data) => {
          // console.log('Fetched PRs:', data)
          prs.value = data
          allPRs.value = data
        })
        .catch((error) => {
          console.error('Error fetching PRs:', error)
        })

      fetch('/api/statistics')
        .then((response) => response.json())
        .then((data) => {
          statistics.value = data
        })
        .catch((error) => {
          console.error('Error fetching statistics:', error)
        })
    }

    fetchData()

    function redFlagRepository(repositoryId) {
      fetch('/api/redFlagRepository', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ repositoryId }),
      })
        .then((response) => response.json())
        .then((data) => {
          console.log('Red-flagged repository:', data)

          // remove the red-flagged repository's PRs from the list
          prs.value = prs.value.filter(
            (pr) => pr.repository._id !== repositoryId
          )
          allPRs.value = allPRs.value.filter(
            (pr) => pr.repository._id !== repositoryId
          )
        })
        .catch((error) => {
          console.error('Error red-flagging repository:', error)
        })
    }

    // Search functionality
    function handleSearchInput() {
      clearTimeout(searchTimeout)
      
      if (!searchQuery.value || searchQuery.value.trim() === '') {
        searchResults.value = []
        return
      }

      searchTimeout = setTimeout(() => {
        fetch(`/api/searchUsers?query=${encodeURIComponent(searchQuery.value)}`)
          .then((response) => response.json())
          .then((data) => {
            searchResults.value = data
          })
          .catch((error) => {
            console.error('Error searching users:', error)
          })
      }, 300) // Debounce 300ms
    }

    function selectUser(user) {
      selectedUser.value = user
      showSearchResults.value = false
      searchQuery.value = user.full_name

      // Fetch user profile and PRs
      fetch(`/api/userProfile/${user._id}`)
        .then((response) => response.json())
        .then((data) => {
          prs.value = data.prs
          userProfileStats.value = data.stats
        })
        .catch((error) => {
          console.error('Error fetching user profile:', error)
        })
    }

    function clearSelection() {
      selectedUser.value = null
      userProfileStats.value = null
      searchQuery.value = ''
      searchResults.value = []
      prs.value = allPRs.value
    }

    // Close search results when clicking outside
    document.addEventListener('click', (e) => {
      if (!e.target.closest('.search-box')) {
        showSearchResults.value = false
      }
    })

    // Computed properties for displayed data
    const displayedPRs = computed(() => {
      return prs.value
    })

    const displayStatistics = computed(() => {
      if (selectedUser.value && userProfileStats.value) {
        return userProfileStats.value
      }
      return statistics.value || {}
    })

    return {
      users,
      colleges,
      owners,
      repositories,
      prs,
      displayedPRs,
      displayStatistics,

      redFlagRepository,
      statistics,
      
      // Search-related
      searchQuery,
      searchResults,
      showSearchResults,
      selectedUser,
      userProfileStats,
      handleSearchInput,
      selectUser,
      clearSelection,
    }
  },
}).mount('#app')
