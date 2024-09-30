import { Link } from "./components/Link";
import MaturityLevels from "../qa/QAPage";


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
    markdownPath: '/udc-react/create-catalogue-entry.md',
  },
  {
    question: "What are the maturity levels?",
    id: "maturity-levels",
    beforeTOC: <>
      <Link label="Maturity Levels" url="/udc-react/tutorial/maturity-levels" />
    </>,
    markdownPath: '/udc-react/maturity-levels.md',
    component: <MaturityLevels />,
  },
  {
    question: "How do I create an organization?",
    id: "create-organization",
    beforeTOC: <>
      <Link label="Create Organization Now" url="/organization/new" />
    </>,
    markdownPath: '/udc-react/create-organization.md',
  },
  {
    question: "How do I add a user to an organization?",
    id: "add-user-to-organization",
    beforeTOC: <>
      <Link label="Add User to Organization" url="/organization" />
    </>,
    markdownPath: '/udc-react/add-user-to-organization.md',
  }
];