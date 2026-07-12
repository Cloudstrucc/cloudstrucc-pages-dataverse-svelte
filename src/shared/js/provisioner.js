import { DataverseClient } from "./dataverse-client.js";
export async function createWebsite(request, client = new DataverseClient()) {
  const draft = await client.create("cs_websites", {
    cs_name: request.websiteName,
    cs_themekey: request.theme,
    cs_defaultlanguage: request.defaultLanguage,
    cs_status: 100000000
  });
  // Production implementation invokes cs_CreateWebsite custom API or a governed flow here.
  return { draft, status: "DraftCreated", requiresProvisioningBackend: true };
}
