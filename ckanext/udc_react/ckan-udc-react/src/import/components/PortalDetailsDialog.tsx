import React from "react";
import { Box, Dialog, DialogContent, DialogTitle, IconButton, Tooltip, Typography } from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { ArcgisPortalCandidate } from "../../api/api";

type PortalDetailsDialogProps = {
  open: boolean;
  onClose: () => void;
  portal?: Partial<ArcgisPortalCandidate> | null;
  arcgisRoot?: string;
};

const ISO_TZ_PATTERN = /(Z|[+-]\d{2}:\d{2})$/;

const formatValue = (value: unknown): string => {
  if (value == null) {
    return "-";
  }
  if (Array.isArray(value)) {
    return value.map((item) => String(item)).join(", ") || "-";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
};

const formatDate = (value: unknown): string => {
  if (value == null || value === "") {
    return "-";
  }
  if (typeof value === "string" || typeof value === "number") {
    const timestamp = typeof value === "string" ? Number(value) : value;
    if (!Number.isFinite(timestamp)) {
      return String(value);
    }
    return new Date(timestamp).toLocaleString();
  }
  return String(value);
};

const asList = (value: unknown): string[] => {
  if (Array.isArray(value)) {
    return value.map((item) => String(item));
  }
  if (value == null) {
    return [];
  }
  return [String(value)];
};

const renderHtml = (value?: string | null) => ({
  __html: value ?? "",
});

const normalizeIsoTimestamp = (value: string): string => {
  if (!value) {
    return value;
  }
  if (ISO_TZ_PATTERN.test(value)) {
    return value;
  }
  return `${value}Z`;
};

const buildThumbnailUrl = (raw: Record<string, unknown>, arcgisRoot?: string): string => {
  const thumbnail = raw?.thumbnail;
  if (typeof thumbnail !== "string" || !thumbnail) {
    return "";
  }
  if (/^https?:\/\//i.test(thumbnail)) {
    return thumbnail;
  }
  const itemId = raw?.id;
  if (typeof itemId !== "string" || !itemId) {
    return "";
  }
  const root = (arcgisRoot || "https://www.arcgis.com").replace(/\/$/, "");
  return `${root}/sharing/rest/content/items/${itemId}/info/${encodeURI(thumbnail)}`;
};

const getExtentCenter = (extent: unknown): { lat: number; lng: number } | null => {
  if (!Array.isArray(extent) || extent.length !== 2) {
    return null;
  }
  const [min, max] = extent;
  if (!Array.isArray(min) || !Array.isArray(max) || min.length < 2 || max.length < 2) {
    return null;
  }
  const minx = Number(min[0]);
  const miny = Number(min[1]);
  const maxx = Number(max[0]);
  const maxy = Number(max[1]);
  if (!Number.isFinite(minx) || !Number.isFinite(miny) || !Number.isFinite(maxx) || !Number.isFinite(maxy)) {
    return null;
  }
  if (Math.abs(minx) > 180 || Math.abs(maxx) > 180 || Math.abs(miny) > 90 || Math.abs(maxy) > 90) {
    return null;
  }
  return { lat: (miny + maxy) / 2, lng: (minx + maxx) / 2 };
};

const buildGoogleMapsEmbedUrl = (extent: unknown): string | null => {
  const center = getExtentCenter(extent);
  if (!center) {
    return null;
  }
  const query = `${center.lat},${center.lng}`;
  return `https://maps.google.com/maps?q=${encodeURIComponent(query)}&z=8&output=embed`;
};

const PortalDetailsDialog: React.FC<PortalDetailsDialogProps> = ({ open, onClose, portal, arcgisRoot }) => {
  const rawDetail = (portal?.raw as Record<string, unknown> | undefined) ?? (portal as Record<string, unknown> | undefined);
  const detail = portal ?? {};
  const thumbnailUrl = buildThumbnailUrl(rawDetail || {}, arcgisRoot);
  const created = rawDetail?.created;
  const modified = rawDetail?.modified;
  const lastViewed = rawDetail?.lastViewed;
  const normalizedCreated = typeof created === "string" ? normalizeIsoTimestamp(created) : created;
  const normalizedModified = typeof modified === "string" ? normalizeIsoTimestamp(modified) : modified;
  const normalizedLastViewed = typeof lastViewed === "string" ? normalizeIsoTimestamp(lastViewed) : lastViewed;
  const extentMapUrl = buildGoogleMapsEmbedUrl(rawDetail?.extent);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", pr: 1 }}>
        <span>Portal Details</span>
        <Tooltip title="Close">
          <IconButton aria-label="Close" onClick={onClose} size="small">
            <CloseIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </DialogTitle>
      <DialogContent>
        <Box sx={{ display: "grid", gridTemplateColumns: "160px 1fr", gap: 1, mb: 2 }}>
          <Typography variant="subtitle2">Title</Typography>
          <Typography variant="body2">{detail.title ?? "-"}</Typography>
          <Typography variant="subtitle2">ID</Typography>
          <Typography variant="body2">{formatValue(rawDetail?.id ?? detail.id)}</Typography>
          <Typography variant="subtitle2">Name</Typography>
          <Typography variant="body2">{formatValue(rawDetail?.name)}</Typography>
          <Typography variant="subtitle2">GUID</Typography>
          <Typography variant="body2">{formatValue(rawDetail?.guid)}</Typography>
          <Typography variant="subtitle2">URL</Typography>
          <Typography variant="body2">
            {detail.url ? (
              <a href={detail.url} target="_blank" rel="noopener noreferrer">
                {detail.url}
              </a>
            ) : (
              "-"
            )}
          </Typography>
          <Typography variant="subtitle2">Portal</Typography>
          <Typography variant="body2">{detail.portalName ?? "-"}</Typography>
          <Typography variant="subtitle2">Org ID</Typography>
          <Typography variant="body2">{detail.orgId ?? "-"}</Typography>
          <Typography variant="subtitle2">Owner</Typography>
          <Typography variant="body2">{formatValue(rawDetail?.owner)}</Typography>
          <Typography variant="subtitle2">Type</Typography>
          <Typography variant="body2">{formatValue(rawDetail?.type)}</Typography>
          <Typography variant="subtitle2">Culture</Typography>
          <Typography variant="body2">{formatValue(rawDetail?.culture)}</Typography>
          <Typography variant="subtitle2">Access</Typography>
          <Typography variant="body2">{formatValue(rawDetail?.access)}</Typography>
          <Typography variant="subtitle2">Content Status</Typography>
          <Typography variant="body2">{formatValue(rawDetail?.contentStatus)}</Typography>
          <Typography variant="subtitle2">Views</Typography>
          <Typography variant="body2">{formatValue(rawDetail?.numViews)}</Typography>
          <Typography variant="subtitle2">Score Completeness</Typography>
          <Typography variant="body2">{formatValue(rawDetail?.scoreCompleteness)}</Typography>
          <Typography variant="subtitle2">Created</Typography>
          <Typography variant="body2">{formatDate(normalizedCreated)}</Typography>
          <Typography variant="subtitle2">Modified</Typography>
          <Typography variant="body2">{formatDate(normalizedModified)}</Typography>
          <Typography variant="subtitle2">Last Viewed</Typography>
          <Typography variant="body2">{formatDate(normalizedLastViewed)}</Typography>
          <Typography variant="subtitle2">Size</Typography>
          <Typography variant="body2">{formatValue(rawDetail?.size)}</Typography>
          <Typography variant="subtitle2">Sub Info</Typography>
          <Typography variant="body2">{formatValue(rawDetail?.subInfo)}</Typography>
          <Typography variant="subtitle2">Listed</Typography>
          <Typography variant="body2">{formatValue(rawDetail?.listed)}</Typography>
          <Typography variant="subtitle2">Comments</Typography>
          <Typography variant="body2">{formatValue(rawDetail?.numComments)}</Typography>
          <Typography variant="subtitle2">Ratings</Typography>
          <Typography variant="body2">{formatValue(rawDetail?.numRatings)}</Typography>
          <Typography variant="subtitle2">Avg Rating</Typography>
          <Typography variant="body2">{formatValue(rawDetail?.avgRating)}</Typography>
          <Typography variant="subtitle2">Access Info</Typography>
          <Typography variant="body2">{formatValue(rawDetail?.accessInformation)}</Typography>
          <Typography variant="subtitle2">Classification</Typography>
          <Typography variant="body2">{formatValue(rawDetail?.classification)}</Typography>
          <Typography variant="subtitle2">Spatial Reference</Typography>
          <Typography variant="body2">{formatValue(rawDetail?.spatialReference)}</Typography>
          <Typography variant="subtitle2">Proxy Filter</Typography>
          <Typography variant="body2">{formatValue(rawDetail?.proxyFilter)}</Typography>
          <Typography variant="subtitle2">Advanced Settings</Typography>
          <Typography variant="body2">{formatValue(rawDetail?.advancedSettings)}</Typography>
          <Typography variant="subtitle2">Group Designations</Typography>
          <Typography variant="body2">{formatValue(rawDetail?.groupDesignations)}</Typography>
          <Typography variant="subtitle2">Token 1 Expiry</Typography>
          <Typography variant="body2">{formatValue(rawDetail?.apiToken1ExpirationDate)}</Typography>
          <Typography variant="subtitle2">Token 2 Expiry</Typography>
          <Typography variant="body2">{formatValue(rawDetail?.apiToken2ExpirationDate)}</Typography>
        </Box>
        <Box sx={{ mb: 2 }}>
          <Typography variant="subtitle2">Snippet</Typography>
          <Box sx={{ wordBreak: "break-word" }} dangerouslySetInnerHTML={renderHtml(detail.snippet ?? "-")} />
        </Box>
        <Box sx={{ mb: 2 }}>
          <Typography variant="subtitle2">Description</Typography>
          <Box sx={{ wordBreak: "break-word" }} dangerouslySetInnerHTML={renderHtml(detail.description ?? "-")} />
        </Box>
        <Box sx={{ mb: 2 }}>
          <Typography variant="subtitle2">Tags</Typography>
          <Typography variant="body2">{asList(detail.tags ?? rawDetail?.tags).join(", ") || "-"}</Typography>
        </Box>
        <Box>
          <Typography variant="subtitle2">Match Reasons</Typography>
          <Typography variant="body2">
            {asList(detail.matchReasons ?? detail.matchedTerms).join(", ") || "-"}
          </Typography>
        </Box>
        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle2">Type Keywords</Typography>
          <Typography variant="body2">{formatValue(rawDetail?.typeKeywords)}</Typography>
        </Box>
        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle2">Categories</Typography>
          <Typography variant="body2">{formatValue(rawDetail?.categories)}</Typography>
        </Box>
        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle2">Access Information</Typography>
          <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
            {formatValue(rawDetail?.accessInformation)}
          </Typography>
        </Box>
        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle2">License Info</Typography>
          <Box
            sx={{ wordBreak: "break-word" }}
            dangerouslySetInnerHTML={renderHtml(String(rawDetail?.licenseInfo ?? "-"))}
          />
        </Box>
        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle2">Extent</Typography>
          <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
            {formatValue(rawDetail?.extent)}
          </Typography>
          {extentMapUrl ? (
            <Box
              sx={{
                mt: 1,
                borderRadius: 1,
                overflow: "hidden",
                border: "1px solid",
                borderColor: "divider",
              }}
            >
              <Box
                component="iframe"
                src={extentMapUrl}
                title="Extent map"
                sx={{ width: "100%", height: 240, border: 0, display: "block" }}
                loading="lazy"
              />
            </Box>
          ) : null}
        </Box>
        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle2">Thumbnail</Typography>
          {thumbnailUrl ? (
            <Box sx={{ mt: 1, display: "flex", alignItems: "center", gap: 2, flexWrap: "wrap" }}>
              <Box
                component="img"
                src={thumbnailUrl}
                alt="Thumbnail"
                sx={{
                  maxWidth: 220,
                  maxHeight: 140,
                  borderRadius: 1,
                  border: "1px solid",
                  borderColor: "divider",
                }}
              />
              <Typography variant="body2" sx={{ wordBreak: "break-word" }}>
                {thumbnailUrl}
              </Typography>
            </Box>
          ) : (
            <Typography variant="body2">{formatValue(rawDetail?.thumbnail)}</Typography>
          )}
        </Box>
        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle2">Documentation</Typography>
          <Typography variant="body2">{formatValue(rawDetail?.documentation)}</Typography>
        </Box>
        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle2">Languages</Typography>
          <Typography variant="body2">{formatValue(rawDetail?.languages)}</Typography>
        </Box>
        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle2">Industries</Typography>
          <Typography variant="body2">{formatValue(rawDetail?.industries)}</Typography>
        </Box>
        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle2">App Categories</Typography>
          <Typography variant="body2">{formatValue(rawDetail?.appCategories)}</Typography>
        </Box>
        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle2">Screenshots</Typography>
          <Typography variant="body2">{formatValue(rawDetail?.screenshots)}</Typography>
        </Box>
        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle2">Banner</Typography>
          <Typography variant="body2">{formatValue(rawDetail?.banner)}</Typography>
        </Box>
        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle2">Large Thumbnail</Typography>
          <Typography variant="body2">{formatValue(rawDetail?.largeThumbnail)}</Typography>
        </Box>
        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle2">Properties</Typography>
          <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
            {formatValue(rawDetail?.properties)}
          </Typography>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default PortalDetailsDialog;
