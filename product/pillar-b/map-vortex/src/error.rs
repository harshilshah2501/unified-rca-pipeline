use thiserror::Error;

pub type Result<T> = std::result::Result<T, Error>;

#[derive(Debug, Error)]
pub enum Error {
    #[error("edge_type not in Motadata closed set: {0}")]
    UnknownEdgeType(String),

    #[error("arrow error: {0}")]
    Arrow(#[from] arrow::error::ArrowError),

    #[error("io error: {0}")]
    Io(#[from] std::io::Error),

    #[error("vortex error: {0}")]
    Vortex(String),

    #[error("column projection missing: {0}")]
    MissingColumn(String),

    #[error("snapshot incomplete or invisible: {0}")]
    IncompleteSnapshot(String),

    #[error("manifest error: {0}")]
    Manifest(String),

    #[error("json error: {0}")]
    Json(#[from] serde_json::Error),
}
