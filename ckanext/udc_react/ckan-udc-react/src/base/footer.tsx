import { Box, Container, Link } from "@mui/material";
import Grid from "@mui/material/Unstable_Grid2/Grid2";
import { REACT_PATH } from "../constants";

export default function Footer() {
  return <Box sx={{
    background: '#002a5c url("../../../base/images/bg.png")',
    padding: "20px 0",
    color: "#CCDEE3",
    fontSize: "0.875rem",
  }}>
    <Container>
      <Grid container>
        <Grid xs={8}>
          <Grid container direction={"column"}>
            <Link href="/about" color="inherit" underline="hover">
              About Canadian Urban Data Catalogue (CUDC)
            </Link>
            <Link href={`/${REACT_PATH}/faq/maturity-levels`} color="inherit" underline="hover">
              Maturity Model FAQ
            </Link>
            <Link href="https://urbandatacentre.ca" color="inherit" underline="hover">
              About Urban Data Centre
            </Link>
          </Grid>
        </Grid>

        <Grid xs={4}>
          <Grid container direction={"column"}>
            <Box sx={{ display: 'flex' }}>
              Powered by
              <Link href="https://urbandatacentre.ca" color="inherit" underline="hover" sx={{ pl: 0.5 }}>
                Urban Data Centre
              </Link></Box>
          </Grid>
        </Grid>
      </Grid>

      <Box sx={{ pb: 2 }} />

    </Container>
  </Box>
}