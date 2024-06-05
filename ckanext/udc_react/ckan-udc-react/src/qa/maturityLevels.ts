export interface Detail {
  category: string;
  label: string;
  shortDescription: string;
  longDescription: string;
  additionalInfo?: { [key: string]: string };
}

export interface MaturityLevel {
  level: number;
  title: string;
  description: string;
  details: Detail[];
}

export interface PageConfig {
  title: string;
  description: string;
  maturityLevels: MaturityLevel[];
}


const maturityLevels: MaturityLevel[] = [
  {
    level: 1,
    title: 'Maturity Level 1 (Basic Information)',
    description: 'Focus on descriptions of what the dataset is about supplemented with temporal and geospatial information.',
    details: [
      { category: 'content', label: 'Domain / Topic', shortDescription: 'Domain or topic of the dataset being cataloged.', longDescription: 'The theme or topic of the package.', additionalInfo: { 'Info 1': 'Additional information 1', 'Info 2': 'Additional information 2' } },
      { category: 'content', label: 'Title', shortDescription: 'Title for the Dataset.', longDescription: 'Title for the dataset. Often assigned by the creator or publisher.' },
      { category: 'content', label: 'Description', shortDescription: 'A description of the dataset.', longDescription: 'A description of the dataset. Often provided by the creator or publisher.' },
      { category: 'content', label: 'Tags', shortDescription: 'Keywords/tags categorizing the dataset.', longDescription: 'Keywords/tags categorizing the dataset. Often provided by the creator or publisher.' },
      { category: 'provenance', label: 'Published Date', shortDescription: 'Published date of the dataset.', longDescription: 'Published date of the dataset. Often provided by the creator or publisher.' },
      { category: 'tempo_geo', label: 'Time Span (start date)', shortDescription: 'Start date of the data in the dataset.', longDescription: 'First date the data was collected for. This is not the date it was collected but the earliest date of the data values.' },
      { category: 'tempo_geo', label: 'Time Span (end date)', shortDescription: 'End date of time data in the dataset.', longDescription: 'Last date the data was collected for. This is not the date it was collected but the latest date of the data values.' },
      { category: 'tempo_geo', label: 'GeoSpatial Area Span', shortDescription: 'A spatial region or named place the dataset covers.', longDescription: 'This data represents the geospatial area the dataset covers. This may be captured as a data column or simply defined by the creator or publisher.' },
    ],
  },
  {
    level: 2,
    title: 'Maturity Level 2 (Content and Ownership)',
    description: 'Focus on the content of the dataset authorship and ownership.',
    details: [
      { category: 'content', label: 'Identifier', shortDescription: 'Unique identifier for the dataset.', longDescription: 'Unique identifier for the dataset. Often assigned by the creator or publisher.' },
      { category: 'access', label: 'Access category', shortDescription: 'Type of access granted for the dataset (open, closed, etc).', longDescription: 'Access category provides a description of the licensing rights for accessing the dataset. Often provided by the rights owner, creator, or publisher.' },
      { category: 'access', label: 'License ID', shortDescription: 'License used to access the dataset.', longDescription: 'License used to access the dataset. Often provided by the creator or publisher.' },
      { category: 'access', label: 'Location', shortDescription: 'Location of the dataset.', longDescription: 'Location where the dataset can be accessed such as a URL.' },
      { category: 'access', label: 'Contact Point', shortDescription: 'Who to contact regarding access.', longDescription: 'The access rights steward is the point of contact (either a person or an organization) to gain access to the dataset. Usually provided by the rights owner, creator, or publisher.' },
      { category: 'ownership', label: 'Data Service', shortDescription: 'Data service for accessing a dataset.', longDescription: 'Data service for accessing a dataset.' },
      { category: 'ownership', label: 'Owner', shortDescription: 'Owner of the dataset.', longDescription: 'Owner\'s name or authoring organization for the dataset.' },
      { category: 'ownership', label: 'Publisher', shortDescription: 'Publisher of the dataset.', longDescription: 'Publisher\'s name or authoring organization for the dataset.' },
      { category: 'ownership', label: 'Publisher Email', shortDescription: 'Email of the publisher.', longDescription: 'Email of the dataset\'s publisher. Can be used to contact the author directly.' },
      { category: 'ownership', label: 'Author', shortDescription: 'Author of the dataset.', longDescription: 'Author\'s name or authoring organization for the dataset.' },
      { category: 'ownership', label: 'Author Email', shortDescription: 'Email of the author.', longDescription: 'Email of the dataset\'s author. Can be used to contact the author directly.' },
      { category: 'content', label: 'Accessed At', shortDescription: 'Date the data and metadata was accessed.', longDescription: 'Date the data and metadata was accessed. This date identifies when the dataset and metadata were reviewed for entry into CUDC. Usually this is provided by data curator or the data owner if provided indirectly from the owner.' },
    ],
  },
  {
    level: 3,
    title: 'Maturity Level 3 (Extended Content)',
    description: 'Focus on additional content and versioning information incorporates some FAIR principles and expands on the temporal and geospatial resolution of the data.',
    details: [
      { category: 'content', label: 'Link to dataset description', shortDescription: 'A URL to an external document describing the dataset.', longDescription: 'A URL to an external document describing the dataset. Often this would be a website that provides additional details about the dataset. It can also link to a document (e.g. PDF) or a resource of some sort (e.g. LinkedData object).' },
      { category: 'content', label: 'Language', shortDescription: 'Language(s) of the dataset.', longDescription: 'Language(s) of the dataset capture what language the data is in. It does not reflect the language of the metadata associated with it.' },
      { category: 'content', label: 'Persistent Identifier', shortDescription: 'Data is identified by a persistent identifier.', longDescription: 'Data is identified by a persistent identifier. A unique identifier can be in any format as long as it is unique within some context. Often this is stored as a unique resource identifier (URI).' },
      { category: 'content', label: 'Globally Unique Identifier', shortDescription: 'Data is identified by a persistent and globally unique identifier.', longDescription: 'Data is identified by a persistent and globally unique identifier. A unique identifier can be in any format as long as it is globally unique. Often this is stored as a unique resource identifier (URI).' },
      { category: 'content', label: 'Version', shortDescription: 'Version of the dataset.', longDescription: 'A literal representing the version of this dataset. It can be a number (e.g. v1.1), a date (e.g. Jan 1 2022), or a textual description (e.g. "First version published for public use").' },
      { category: 'access', label: 'Format (CSV, XLS, TXT, PDF, etc)', shortDescription: 'Format of the dataset.', longDescription: 'Format of the dataset can indicate its file type (e.g. csv, pdf, ttl).' },
      { category: 'access', label: 'Source', shortDescription: 'Source of the dataset.', longDescription: 'Source where the dataset can be accessed such as a URL.' },
      { category: 'provenance', label: 'Version notes', shortDescription: 'Version notes about the dataset.', longDescription: 'Additional information about the version such as date it was published, reasons for publishing, etc.' },
      { category: 'provenance', label: 'Is version of another dataset', shortDescription: 'Link to dataset that it is a version of.', longDescription: 'Link to dataset that it is a version of.' },
      { category: 'provenance', label: 'Other versions', shortDescription: 'Link to datasets that are versions of it.', longDescription: 'Link to datasets that are versions of it.' },
      { category: 'provenance', label: 'Provenance Text', shortDescription: 'Provenance Text of the data.', longDescription: 'Provenance of the data identifying who created the previous versions, who has used them, etc.' },
      { category: 'provenance', label: 'Provenance URL', shortDescription: 'Provenance URL of the data.', longDescription: 'The source URL for the provenance of the data' },
      { category: 'tempo_geo', label: 'Temporal resolution', shortDescription: 'Describes how granular the date/time data in the dataset is.', longDescription: 'Describes how granular the date/time data in the dataset is. Usually this explains the level of aggregation provided by the dataset. For example, time-series data can be by minute, hour, year, or season.' },
      { category: 'tempo_geo', label: 'GeoSpatial resolution in meters', shortDescription: 'Describes how granular (in meters) geospatial data is in the dataset.', longDescription: 'Describes how granular (in meters) geospatial data is in the dataset. Usually this explains the level of aggregation provided by the dataset. For example, geospatial information can be stored in 1 meter detail, 5 meters, 1000 meters, etc.' },
      { category: 'tempo_geo', label: 'GeoSpatial resolution (in regions)', shortDescription: 'Describes how granular (in regions) geospatial data is in the dataset.', longDescription: 'Describes how granular (in regions) geospatial data is in the dataset. Usually this explains the level of aggregation provided by the dataset. For example, geospatial information can be at the city, province, region, or country level. It can also be stored as a polygon defined by longitude/latitude coordinates.' },
    ],
  },
  {
    level: 4,
    title: 'Maturity Level 4 (Privacy Indigenous data)',
    description: 'Focus on privacy and identifying data of individuals captured by the dataset including guidelines for Indigenous communities.',
    details: [
      { category: 'content', label: 'Contains Individual Data', shortDescription: 'Does the data hold individualized data?', longDescription: 'Does the data hold individualized data? If yes, the dataset is aggregated at the individual level.' },
      { category: 'content', label: 'Contains Identifiable Data', shortDescription: 'Does the data hold identifiable individual data?', longDescription: 'Does the data hold identifiable individual data that can be used to uniquely identify an individual data was collected about? If yes, the dataset is not anonymized.' },
      { category: 'content', label: 'Contains Indigenous Data', shortDescription: 'Does the data hold data about Indigenous communities?', longDescription: 'Does the data hold data about Indigenous communities? If yes, the dataset should comply with OCAP principles (Ownership, Control, Access, Possession). See https://fnigc.ca/ocap-training/ for more information.' },
      { category: 'access', label: 'Limits on use', shortDescription: 'Limits on use of data.', longDescription: 'Limits on use (e.g. academic purposes). Information provided generally provides more detail on the terms and access rights beyond the license. Usually provided by the rights owner, creator, or publisher.' },
      { category: 'access', label: 'Indigenous Community Permission', shortDescription: 'Who holds the Indigenous Community Permission. Who to contact regarding access to a dataset that has data about Indigenous communities.', longDescription: 'Who holds the Indigenous Community Permission. The Indigenous access rights steward is the point of contact (either a person or an organization) to gain access to the dataset. It is an agent that has the right to manage access rights to Indigenous data. That person can be Indigenous themselves or a non-Indigenous agent that acts as the steward for access rights to the data. Usually provided by the previous rights owner, creator, or publisher.' },
      { category: 'tempo_geo', label: 'The Indigenous communities the dataset is about', shortDescription: 'Indigenous communities from which data is derived.', longDescription: 'Indigenous communities from which data is derived. This represents the community coverage of the communities that provided the data or are the subject of data stored in the dataset.' },
    ],
  },
  {
    level: 5,
    title: 'Maturity Level 5 (FAIR)',
    description: 'Focus on FAIR principles: Findable, Accessible, Interoperable, Retrievable.',
    details: [
      { category: 'content', label: 'Data complies with a community standard (RDA-R1.3-01D)', shortDescription: 'This indicator requires that data complies with community standards. (FAIR ID = RDA-R1.3-01D).', longDescription: 'This indicator is linked to the following principle: R1.3: (Meta)data meet domain relevant community standards. The indicator can be evaluated by verifying that the data follows a community standard. A service like the RDA-endorsed FAIR-sharing could be helpful to identify the relevant standards. The indicator can be evaluated by verifying that the data follows a community standard. A service like the RDA-endorsed FAIR-sharing could be helpful to identify the relevant standards.' },
      { category: 'content', label: 'Data uses knowledge representation expressed in standardised format (RDA-I1-01D)', shortDescription: 'The indicator serves to determine that an appropriate standard is used to express knowledge in particular the data model and format (FAIR ID = RDA-I1-01D).', longDescription: 'This indicator is linked to the following principle: I1: (Meta)data use a formal, accessible, shared and broadly applicable language for knowledge representation. The indicator can be evaluated by looking at information about the data model and format, verifying that the standard used is appropriate for the domain and the type of digital object. Deciding on the appropriateness of the knowledge representation may be based on its inclusion in a registry like the one developed by FAIR-sharing.' },
      { category: 'content', label: 'Data uses machine-understandable knowledge representation (RDA-I1-02D)', shortDescription: 'This indicator focuses on the machine-understandability aspect of the data. This means that data should be readable and thus interoperable for machines without any requirements such as specific translators or mappings (FAIR ID = RDA-I1-02D).', longDescription: 'This indicator is linked to the following principle: I1: (Meta)data use a formal, accessible, shared and broadly applicable language for knowledge representation. This indicator can be evaluated by looking at the knowledge representation model used for the expression of the data. Examples are RDF, OWL, JSON-LD, Data Cube, the Generalized Data Model for clinical research, and SKOS. Information about models and formats can be looked up in a registry like the RDA endorsed FAIR-sharing (see for example: https://fairsharing.org/standards/?q=&selected_facets=type_exact:model/format).' },
      { category: 'content', label: 'Data uses FAIR-compliant vocabularies (RDA-I2-01D)', shortDescription: 'The indicator requires the controlled vocabulary used for the data to conform to the FAIR principles and at least be documented and resolvable using globally unique and persistent identifiers. The documentation needs to be easily findable and accessible (FAIR ID = RDA-I2-01D).', longDescription: 'This indicator is linked to the following principle: I2: (Meta)data use vocabularies that follow the FAIR principles. The indicator can be evaluated by verifying that each of the vocabularies used in the data is documented and resolvable using globally unique and persistent identifiers with the documentation being easily findable and accessible. Typically, the reference to the specification of the vocabularies used will be included in the documentation of the digital object or the repository where it is kept.' },
      { category: 'content', label: 'Data includes references to other data (RDA-I3-01D)', shortDescription: 'This indicator is about the way data is connected to other data, for example linking to previous or related research data that provides additional context to the data (FAIR ID = RDA-I3-01D).', longDescription: 'This indicator is linked to the following principle: I3: (Meta)data include qualified references to other (meta)data. The indicator can be evaluated by looking at the presence of references to other data in the data. For example, there may be links to other resources in cells in a spreadsheet or in RDF-based data.' },
      { category: 'access', label: 'Data is accessible through an access protocol that supports authentication and authorisation (RDA-A1.2-01D)', shortDescription: 'The indicator requires that if the data or local environment indicates a degree of additional protection, then the access protocol must support authentication and authorisation of people and/or machines? (FAIR ID = RDA-A1.2-01D).', longDescription: 'This indicator is linked to the following principle: A1.2: The protocol allows for an authentication and authorisation where necessary. The indicator can be evaluated by assessing whether an authentication and authorisation process is present in the protocol (e.g. HMAC).' },
      { category: 'access', label: 'Data can be accessed manually (RDA-A1-02D)', shortDescription: 'Data can be accessed manually (i.e. with human intervention FAIR ID = RDA-A1-02D).', longDescription: 'The indicator refers to any human interactions that are needed if the requester wants to access the digital object. The FAIR principle refers mostly to automated interactions where a machine is able to access the digital object but there may also be digital objects that require human interactions such as clicking on a link on a landing page, sending an e-mail to the data owner or even calling by telephone. This indicator is linked to the following principle: A1: (Meta)data are retrievable by their identifier using a standardised communication protocol. The indicator can be evaluated by looking for information in the metadata that describes how access to the digital object can be obtained through human intervention.' },
      { category: 'access', label: 'Data identifier resolves to a digital object (RDA-A1-03D)', shortDescription: 'Data identifier resolves to a digital object (FAIR ID = RDA-A1-03D)', longDescription: 'This indicator is about the resolution of the identifier that identifies the digital object. The identifier assigned to the data should be associated with a formally defined retrieval/resolution mechanism that enables access to the digital object or provides access instructions for access in the case of human-mediated access. The FAIR principle and this indicator do not say anything about the mutability or immutability of the digital object that is identified by the data identifier -- this is an aspect that should be governed by a persistence policy of the data provider. This indicator is linked to the following principle: A1: (Meta)data are retrievable by their identifier using a standardised communication protocol. The indicator can be evaluated by invoking the mechanism specific to the protocol (e.g. GET for HTTP) and verifying that this delivers the digital object.' },
      { category: 'access', label: 'Data is accessible through a standardised protocol (RDA-A1-04D)', shortDescription: 'The indicator refers to automated interactions between machines to access digital objects (FAIR ID = RDA-A1-04D).', longDescription: 'The indicator reflects the way machines interact and grant access to the digital object. This indicator is linked to the following principle: A1: (Meta)data are retrievable by their identifier using a standardised communication protocol. This indicator can be evaluated by resolving the link to the data, e.g. by resolving the persistent identifier and verifying that the data is reached. In the common case that the identifier is an HTTP URI, this can be done using the HTTP GET method. The evaluator or evaluation tool may also want to verify that the resolution delivers the correct data.' },
      { category: 'access', label: 'Data can be accessed automatically (RDA-A1-05D)', shortDescription: 'Data can be accessed automatically (i.e. by a computer program FAIR ID = RDA-A1-05D)', longDescription: 'The indicator refers to automated interactions between machines to access digital objects. The way machines interact and grant access to the digital object will be evaluated by the indicator. This indicator is linked to the following principle: A1: (Meta)data are retrievable by their identifier using a standardised communication protocol. This indicator can be evaluated by resolving the link to the data, e.g. by resolving the persistent identifier and verifying that the data is reached. In the common case that the identifier is an HTTP URI, this can be done using the HTTP GET method. The evaluator or evaluation tool may also want to verify that the resolution delivers the correct data.' },
      { category: 'access', label: 'Data is accessible through a free access protocol (RDA-A1.1-01D)', shortDescription: 'The indicator requires that the protocol can be used free of charge, which facilitates unfettered access (FAIR ID = RDA-A1.1-01D).', longDescription: 'This indicator is linked to the following principle: A1.1: The protocol is open, free, and universally implementable. This indicator can be evaluated by verifying that the protocol is free of charge. This is the case for most protocols in use, for example, HTTP and FTP.' },
    ],
  },
  {
    level: 6,
    title: 'Maturity Level 6 (Quality and Quantity)',
    description: 'Focus on the statistics and quality of the data in the dataset.',
    details: [
      { category: 'statistical', label: 'Number of data rows', shortDescription: 'If tabular dataset, total number of rows.', longDescription: 'If tabular dataset, total number of data rows. Tabular could be a CSV file, an Excel file, a relational database, etc.' },
      { category: 'statistical', label: 'Number of data columns', shortDescription: 'If tabular dataset, total number of unique columns.', longDescription: 'If tabular dataset, total number of unique columns across all sheets (if an Excel type file). Tabular could be a CSV file, an Excel file, a relational database, etc.' },
      { category: 'statistical', label: 'Number of data cells', shortDescription: 'If tabular dataset, total number of cells with data.', longDescription: 'If tabular dataset, total number of data cells with data, i.e. not empty cells. Tabular could be a CSV file, an Excel file, a relational database, etc.' },
      { category: 'statistical', label: 'Number of data relations', shortDescription: 'If RDF dataset, total number of triples.', longDescription: 'If RDF dataset, total number of triples.' },
      { category: 'statistical', label: 'Number of entities', shortDescription: 'If RDF dataset, total number of entities.', longDescription: 'If RDF dataset, total number of entities (i.e. concepts used in the dataset).' },
      { category: 'statistical', label: 'Number of data properties', shortDescription: 'If RDF dataset, total number of unique properties used by the triples.', longDescription: 'If RDF dataset, total number of unique properties used in this dataset.' },
      { category: 'statistical', label: 'Data quality', shortDescription: 'Describes the quality of the data in the dataset.', longDescription: 'Quality of the data can be a simple description (e.g. "high quality for 80%"), a simple scale (e.g. "3 out of 4"), or specific values and metrics (e.g. "80% of cells are missing").' },
      { category: 'statistical', label: 'Metric for data quality', shortDescription: 'A metric used to measure the quality of the data, such as missing values or invalid formats.', longDescription: 'Quality metrics can be any metrics used to measure the quality of the dataset as a whole. For example, the VIMO metrics are used to measure how many cells are valid, invalid, missing, or outliers.' },
    ],
  },
];

export const qaPageConfig = {
  title: 'Maturity Levels',
  description: 'This page provides information on different maturity levels, each with specific details and criteria to help evaluate datasets.',
  maturityLevels,
};


export const configSchema = {
  type: "object",
  properties: {
    title: { type: "string" },
    description: { type: "string" },
    maturityLevels: {
      type: "array",
      items: {
        type: "object",
        properties: {
          level: { type: "number" },
          title: { type: "string" },
          description: { type: "string" },
          details: {
            type: "array",
            items: {
              type: "object",
              properties: {
                category: { type: "string" },
                label: { type: "string" },
                shortDescription: { type: "string" },
                longDescription: { type: "string" },
                additionalInfo: {
                  type: "object",
                  additionalProperties: { type: "string" },
                },
              },
              required: ["category", "label", "shortDescription", "longDescription"]
            },
          },
        },
        required: ["level", "title", "description", "details"]
      },
    },
  },
  required: ["title", "description", "maturityLevels"]
};
