import { request, requestBlob } from "./httpClient.js";

const mapFloor = (floor) => ({
  id: floor.id,
  projectId: floor.project_id,
  code: floor.code,
  name: floor.name,
  levelOrder: floor.level_order,
  floorType: floor.floor_type,
  hasDwg: floor.has_dwg,
  hasValidDwg: floor.has_valid_dwg,
  latestDwgVersion: floor.latest_dwg_version,
  dwgVersions: (floor.dwg_versions ?? []).map(mapVersion),
  dwgReferenceConfirmed: floor.dwg_reference_confirmed,
  dwgReferenceConfirmedAt: floor.dwg_reference_confirmed_at,
  dwgReferenceConfirmedByUserId:
    floor.dwg_reference_confirmed_by_user_id,
});

function mapVersion(version) {
  return {
  id: version.id,
  version: version.version,
  originalFilename: version.original_filename,
  standardizedFilename: version.standardized_filename,
  mimeType: version.mime_type,
  sizeBytes: version.size_bytes,
  sha256: version.sha256,
  signature: version.dwg_signature,
  isReadable: version.is_readable,
  uploadedByUserId: version.uploaded_by_user_id,
  uploadedAt: version.uploaded_at,
  };
}

export const dwgService = Object.freeze({
  getFloors: async (pilotId) =>
    (await request(`/pilots/${pilotId}/floors`)).map(mapFloor),
  createFloor: async (pilotId, values) =>
    mapFloor(
      await request(`/pilots/${pilotId}/floors`, {
        method: "POST",
        body: JSON.stringify({
          code: values.code.toUpperCase(),
          name: values.name,
          level_order: Number(values.levelOrder),
          floor_type: values.floorType,
        }),
      }),
    ),
  deleteFloor: (floorId) =>
    request(`/floors/${floorId}`, { method: "DELETE" }),
  setReferenceConfirmation: async (floorId, confirmed) =>
    mapFloor(
      await request(`/floors/${floorId}/dwg-reference`, {
        method: "PUT",
        body: JSON.stringify({ confirmed }),
      }),
    ),
  getVersions: async (floorId) =>
    (await request(`/floors/${floorId}/dwg/versions`)).map(mapVersion),
  upload: async (floorId, file) => {
    const body = new FormData();
    body.append("file", file);
    return mapVersion(
      await request(`/floors/${floorId}/dwg`, { method: "POST", body }),
    );
  },
  download: (versionId) =>
    requestBlob(`/dwg/versions/${versionId}/download`),
});
