# Knowledge Graph API

This document describes the API endpoint for retrieving knowledge graphs of catalogue entries.

## Overview

The knowledge graph API returns the RDF graph directly with appropriate content-type headers, without JSON wrapping.

## Endpoint

Returns the RDF graph directly with appropriate content-type headers.

### Endpoint

```
GET /catalogue/<package_id>/graph[.format]
```

### URL Parameters

| Parameter    | Type   | Required | Description                    |
|--------------|--------|----------|--------------------------------|
| `package_id` | string | Yes      | Package ID or name             |
| `format`     | string | No       | File extension (ttl, jsonld, etc.) |

### Query Parameters

| Parameter | Type   | Required | Default  | Description                                    |
|-----------|--------|----------|----------|------------------------------------------------|
| `format`  | string | No       | `turtle` | RDF serialization format (overrides URL extension) |

### Supported Formats

- `turtle` or `ttl` - Turtle format (default)
- `json-ld` or `jsonld` - JSON-LD format
- `xml` or `rdf` - RDF/XML format
- `n3` - Notation3 format
- `nt` - N-Triples format

### Response

Returns raw RDF data with appropriate `Content-Type` header:

- `text/turtle; charset=utf-8` for Turtle
- `application/ld+json; charset=utf-8` for JSON-LD
- `application/rdf+xml; charset=utf-8` for RDF/XML
- `text/n3; charset=utf-8` for N3
- `application/n-triples; charset=utf-8` for N-Triples

### Examples

```bash
# Get graph in Turtle format (default)
curl "http://localhost:5000/catalogue/my-package-name/graph"

# Get graph using file extension
curl "http://localhost:5000/catalogue/my-package-name/graph.ttl"
curl "http://localhost:5000/catalogue/my-package-name/graph.jsonld"
curl "http://localhost:5000/catalogue/my-package-name/graph.rdf"

# Get graph using query parameter
curl "http://localhost:5000/catalogue/my-package-name/graph?format=json-ld"
```

### Error Responses

- **400 Bad Request**: Invalid format
- **403 Forbidden**: Not authorized to access package
- **404 Not Found**: Package not found
- **503 Service Unavailable**: GraphDB is disabled

## Authentication

This endpoint uses the same authentication as the `package_show` action. If the package is public, no authentication is required. For private packages, you need to provide an API key using the `Authorization` header.

## Sample Outputs

### Turtle Format

```turtle
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .

<http://data.urbandatacentre.ca/catalogue/550e8400-e29b-41d4-a716-446655440000>
    a dcat:Dataset ;
    dcterms:title "My Dataset Title"@en ;
    dcterms:description "Dataset description"@en ;
    dcat:theme <http://data.urbandatacentre.ca/theme/transportation> ;
    dcterms:publisher [
        a foaf:Organization ;
        foaf:name "Example Organization"
    ] .
```

### JSON-LD Format

```json
{
  "@context": {
    "dcterms": "http://purl.org/dc/terms/",
    "dcat": "http://www.w3.org/ns/dcat#",
    "foaf": "http://xmlns.com/foaf/0.1/"
  },
  "@id": "http://data.urbandatacentre.ca/catalogue/550e8400-e29b-41d4-a716-446655440000",
  "@type": "dcat:Dataset",
  "dcterms:title": {
    "@language": "en",
    "@value": "My Dataset Title"
  },
  "dcterms:description": {
    "@language": "en",
    "@value": "Dataset description"
  }
}
```

## Error Responses (detailed)

### 400 Bad Request - Invalid Format

```
Invalid format 'xyz'. Must be one of: turtle, json-ld, xml, n3, nt, pretty-xml
```

### 403 Forbidden - No Permission

```
Not authorized to access this package
```

### 404 Not Found - Package Not Found

```
Package not found: invalid-id
```

### 503 Service Unavailable - GraphDB Disabled

```
Knowledge graph feature is disabled. GraphDB connection is not available.
```

## Implementation Notes

1. **SPARQL Query**: The API constructs a SPARQL CONSTRUCT query to retrieve all triples where the catalogue URI is the subject, plus any referenced blank nodes (e.g., distribution information).

2. **URI Construction**: The catalogue URI is constructed from the mapping configuration's `@id` field template, ensuring consistency with the knowledge graph storage.

3. **Authorization**: The action uses the same authorization as `package_show`, so users can only retrieve graphs for packages they have permission to view.

4. **Empty Graphs**: If no triples are found for the package (e.g., it hasn't been synced to the knowledge graph yet), an empty graph will be returned in the requested format.

5. **Performance**: The query retrieves all triples related to the catalogue entry in a single SPARQL query, which is efficient for most use cases.

## Testing

Test the endpoint with curl:

```bash
# Test with default format (turtle)
curl http://localhost:5000/catalogue/my-package-name/graph

# Test with different formats
curl http://localhost:5000/catalogue/my-package-name/graph.ttl
curl http://localhost:5000/catalogue/my-package-name/graph.jsonld
curl http://localhost:5000/catalogue/my-package-name/graph.rdf
```

## Use Cases

1. **Data Export**: Export catalogue metadata in standard RDF formats for external systems
2. **Linked Data**: Enable linked data applications to consume catalogue metadata
3. **Backup**: Create backups of knowledge graph data in portable formats
4. **Analysis**: Analyze catalogue metadata using RDF tools and SPARQL
5. **Integration**: Integrate with semantic web applications and triple stores
6. **Validation**: Validate RDF graph structure and content

## See Also

- [CKAN API Guide](https://docs.ckan.org/en/latest/api/)
- [RDF 1.1 Concepts](https://www.w3.org/TR/rdf11-concepts/)
- [JSON-LD 1.1](https://www.w3.org/TR/json-ld11/)
- [Turtle](https://www.w3.org/TR/turtle/)
