const JD_DB_NAME = 'aria_jd_cache'
const JD_STORE_NAME = 'jd_files'
const JD_DB_VERSION = 1

function openJdDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(JD_DB_NAME, JD_DB_VERSION)
    request.onerror = () => reject(request.error)
    request.onsuccess = () => resolve(request.result)
    request.onupgradeneeded = (event) => {
      const db = event.target.result
      if (!db.objectStoreNames.contains(JD_STORE_NAME)) {
        db.createObjectStore(JD_STORE_NAME)
      }
    }
  })
}

export async function storeJdFile(file) {
  const db = await openJdDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(JD_STORE_NAME, 'readwrite')
    const store = tx.objectStore(JD_STORE_NAME)
    const req = store.put(file, 'jd_file')
    req.onsuccess = () => resolve()
    req.onerror = () => reject(req.error)
  })
}

export async function getJdFile() {
  const db = await openJdDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(JD_STORE_NAME, 'readonly')
    const store = tx.objectStore(JD_STORE_NAME)
    const req = store.get('jd_file')
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

export async function clearJdFile() {
  const db = await openJdDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(JD_STORE_NAME, 'readwrite')
    const store = tx.objectStore(JD_STORE_NAME)
    const req = store.delete('jd_file')
    req.onsuccess = () => resolve()
    req.onerror = () => reject(req.error)
  })
}
