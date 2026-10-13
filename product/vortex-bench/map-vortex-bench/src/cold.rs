//! Coldness helpers for Action 4: process-cold vs disk-cold vs warm.

use anyhow::{Context, Result};
use std::fs::File;
use std::io::Read;
use std::path::{Path, PathBuf};

/// Advise the kernel that part-file pages can be dropped from page cache.
/// Best-effort (no root required). Not a guarantee of full cache eviction.
pub fn drop_file_page_cache(path: &Path) -> Result<()> {
    let file = File::open(path).with_context(|| format!("open for fadvise {}", path.display()))?;
    let len = file.metadata()?.len();
    #[cfg(target_os = "linux")]
    {
        use std::os::unix::io::AsRawFd;
        // POSIX_FADV_DONTNEED = 4
        let _rc = libc_fadvise(file.as_raw_fd(), 0, len as i64, 4);
    }
    let _ = (file, len);
    Ok(())
}

#[cfg(target_os = "linux")]
fn libc_fadvise(fd: i32, offset: i64, len: i64, advice: i32) -> i32 {
    // SAFETY: fd from File::as_raw_fd; advice is POSIX_FADV_DONTNEED.
    unsafe { libc::posix_fadvise(fd, offset, len, advice) }
}

pub fn drop_parts_page_cache(nodes: &Path, edges: &Path) -> Result<()> {
    drop_file_page_cache(nodes)?;
    drop_file_page_cache(edges)?;
    // Give the kernel a moment; not strictly required.
    std::thread::sleep(std::time::Duration::from_millis(5));
    Ok(())
}

/// Touch both files fully so subsequent loads are page-cache warm.
pub fn warm_parts_page_cache(nodes: &Path, edges: &Path) -> Result<()> {
    for p in [nodes, edges] {
        let mut f = File::open(p)?;
        let mut buf = vec![0u8; 1 << 20];
        loop {
            let n = f.read(&mut buf)?;
            if n == 0 {
                break;
            }
        }
    }
    Ok(())
}

/// Copy parts into a fresh staging directory (remote-fetch proxy for Action 4).
/// Caller should then disk-cold the copies before load.
pub fn stage_remote_proxy_copy(
    nodes: &Path,
    edges: &Path,
    staging_dir: &Path,
) -> Result<(PathBuf, PathBuf)> {
    std::fs::create_dir_all(staging_dir)?;
    let n_out = staging_dir.join("nodes.vortex");
    let e_out = staging_dir.join("edges.vortex");
    std::fs::copy(nodes, &n_out)?;
    std::fs::copy(edges, &e_out)?;
    Ok((n_out, e_out))
}
