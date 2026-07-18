export function createPinnedLookup(records) {
  const pinned = records.map(record => ({
    address: String(record.address),
    family: Number(record.family),
  }));
  return (_hostname, options, callback) => {
    if (typeof options === "function") {
      callback = options;
      options = {};
    }
    if (options?.all) {
      callback(null, pinned.map(record => ({ ...record })));
      return;
    }
    callback(null, pinned[0].address, pinned[0].family);
  };
}
