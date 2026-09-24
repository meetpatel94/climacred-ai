import { useEffect, useState } from 'react';

/** Bumps after a successful Data Import so open pages reload stored datasets. */
export function useImportedDataRevision(): number {
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const onImported = () => setRevision((value) => value + 1);
    window.addEventListener('climacred:data-imported', onImported);
    return () => window.removeEventListener('climacred:data-imported', onImported);
  }, []);
  return revision;
}
