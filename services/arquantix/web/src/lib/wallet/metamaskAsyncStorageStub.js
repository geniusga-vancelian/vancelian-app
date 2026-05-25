/** Stub web pour `@react-native-async-storage/async-storage` (MetaMask SDK, optionnel). */
const memory = new Map()

module.exports = {
  getItem: async (key) => memory.get(key) ?? null,
  setItem: async (key, value) => {
    memory.set(key, value)
  },
  removeItem: async (key) => {
    memory.delete(key)
  },
  clear: async () => {
    memory.clear()
  },
  getAllKeys: async () => [...memory.keys()],
  multiGet: async (keys) => keys.map((key) => [key, memory.get(key) ?? null]),
  multiSet: async (pairs) => {
    for (const [key, value] of pairs) memory.set(key, value)
  },
  multiRemove: async (keys) => {
    for (const key of keys) memory.delete(key)
  },
}
