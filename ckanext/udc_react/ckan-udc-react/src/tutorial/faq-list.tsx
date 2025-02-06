import { Link } from "./components/Link";
import MaturityLevels from "../qa/QAPage";
import { REACT_PATH } from "../constants";


export interface FAQ {
  question: string;
  id: string;
  beforeTOC: React.ReactNode;
  markdown?: string;
  markdownPath?: string;
  component?: React.ReactNode;
}

export const FAQList: FAQ[] = [
  {
    question: "How do I create a catalogue entry?",
    id: "create-catalogue-entry",
    beforeTOC: <>
      <Link label="Create Catalogue Entry Now" url="/catalogue/new" />
      <Link label="Create Organization Now" url="/organization/new" />
    </>,
    markdownPath: `/${REACT_PATH}/create-catalogue-entry.md`,
  },
  {
    question: "What are the maturity levels?",
    id: "maturity-levels",
    beforeTOC: <>
      <Link label="Maturity Levels" url={`/${REACT_PATH}/tutorial/maturity-levels`} />
    </>,
    markdownPath: '/${REACT_PATH}/maturity-levels.md',
    component: <MaturityLevels />,
  },
  {
    question: "How do I create an organization?",
    id: "create-organization",
    beforeTOC: <>
      <Link label="Create Organization Now" url="/organization/new" />
    </>,
    markdownPath: `/${REACT_PATH}/create-organization.md`,
  },
  {
    question: "How do I add a user to an organization?",
    id: "add-user-to-organization",
    beforeTOC: <>
      <Link label="Add User to Organization" url="/organization" />
    </>,
    markdownPath: `/${REACT_PATH}/add-user-to-organization.md`,
  }
];