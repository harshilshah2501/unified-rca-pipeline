//! Closed Motadata ``edge_type`` set (fifteen SCREAMING names).

use crate::error::{Error, Result};
use serde::{Deserialize, Serialize};
use std::fmt;
use std::str::FromStr;

/// Motadata storage ``edge_type`` values admitted on ``map_edges``.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum EdgeType {
    DependsOn,
    RunsOn,
    Mounts,
    ConnectsTo,
    Backs,
    Uses,
    HostedOn,
    MemberOf,
    PartOf,
    RoutesThrough,
    AuthenticatesVia,
    MonitoredBy,
    BackedUpBy,
    ClusteredWith,
    CommunicatesWith,
}

impl EdgeType {
    pub const ALL: &'static [EdgeType] = &[
        Self::DependsOn,
        Self::RunsOn,
        Self::Mounts,
        Self::ConnectsTo,
        Self::Backs,
        Self::Uses,
        Self::HostedOn,
        Self::MemberOf,
        Self::PartOf,
        Self::RoutesThrough,
        Self::AuthenticatesVia,
        Self::MonitoredBy,
        Self::BackedUpBy,
        Self::ClusteredWith,
        Self::CommunicatesWith,
    ];

    pub fn as_str(self) -> &'static str {
        match self {
            Self::DependsOn => "DEPENDS_ON",
            Self::RunsOn => "RUNS_ON",
            Self::Mounts => "MOUNTS",
            Self::ConnectsTo => "CONNECTS_TO",
            Self::Backs => "BACKS",
            Self::Uses => "USES",
            Self::HostedOn => "HOSTED_ON",
            Self::MemberOf => "MEMBER_OF",
            Self::PartOf => "PART_OF",
            Self::RoutesThrough => "ROUTES_THROUGH",
            Self::AuthenticatesVia => "AUTHENTICATES_VIA",
            Self::MonitoredBy => "MONITORED_BY",
            Self::BackedUpBy => "BACKED_UP_BY",
            Self::ClusteredWith => "CLUSTERED_WITH",
            Self::CommunicatesWith => "COMMUNICATES_WITH",
        }
    }

    /// Ingest snake_case ``relation`` for this Motadata ``edge_type``.
    pub fn ingest_relation(self) -> &'static str {
        match self {
            Self::DependsOn => "depends_on",
            Self::RunsOn => "runs_on",
            Self::Mounts => "mounts",
            Self::ConnectsTo => "connects_to",
            Self::Backs => "backs",
            Self::Uses => "uses",
            Self::HostedOn => "hosted_on",
            Self::MemberOf => "member_of",
            Self::PartOf => "part_of",
            Self::RoutesThrough => "routes_through",
            Self::AuthenticatesVia => "authenticates_via",
            Self::MonitoredBy => "monitored_by",
            Self::BackedUpBy => "backed_up_by",
            Self::ClusteredWith => "clustered_with",
            Self::CommunicatesWith => "communicates_with",
        }
    }

    pub fn from_ingest(relation: &str) -> Option<Self> {
        match relation {
            "depends_on" => Some(Self::DependsOn),
            "runs_on" => Some(Self::RunsOn),
            "mounts" => Some(Self::Mounts),
            "connects_to" => Some(Self::ConnectsTo),
            "backs" => Some(Self::Backs),
            "uses" => Some(Self::Uses),
            "hosted_on" => Some(Self::HostedOn),
            "member_of" => Some(Self::MemberOf),
            "part_of" => Some(Self::PartOf),
            "routes_through" => Some(Self::RoutesThrough),
            "authenticates_via" => Some(Self::AuthenticatesVia),
            "monitored_by" => Some(Self::MonitoredBy),
            "backed_up_by" => Some(Self::BackedUpBy),
            "clustered_with" => Some(Self::ClusteredWith),
            "communicates_with" => Some(Self::CommunicatesWith),
            _ => None,
        }
    }
}

impl fmt::Display for EdgeType {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

impl FromStr for EdgeType {
    type Err = Error;

    fn from_str(s: &str) -> Result<Self> {
        match s {
            "DEPENDS_ON" => Ok(Self::DependsOn),
            "RUNS_ON" => Ok(Self::RunsOn),
            "MOUNTS" => Ok(Self::Mounts),
            "CONNECTS_TO" => Ok(Self::ConnectsTo),
            "BACKS" => Ok(Self::Backs),
            "USES" => Ok(Self::Uses),
            "HOSTED_ON" => Ok(Self::HostedOn),
            "MEMBER_OF" => Ok(Self::MemberOf),
            "PART_OF" => Ok(Self::PartOf),
            "ROUTES_THROUGH" => Ok(Self::RoutesThrough),
            "AUTHENTICATES_VIA" => Ok(Self::AuthenticatesVia),
            "MONITORED_BY" => Ok(Self::MonitoredBy),
            "BACKED_UP_BY" => Ok(Self::BackedUpBy),
            "CLUSTERED_WITH" => Ok(Self::ClusteredWith),
            "COMMUNICATES_WITH" => Ok(Self::CommunicatesWith),
            other => Err(Error::UnknownEdgeType(other.to_string())),
        }
    }
}
