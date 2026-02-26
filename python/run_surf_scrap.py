# run_surf_scrap.py

import argparse
from surf_scrap import scrape_surf_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape Surf-Report et exporte en CSV.")
    parser.add_argument(
        "--url",
        required=True,
        help="URL Surf-Report (ex: https://www.surf-report.com/meteo-surf/lacanau-s1043.html)"
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Chemin du CSV de sortie (ex: ./lacanau.csv) ou dossier (ex: ./data/). "
             "Si omis: ./data_surf.csv"
    )
    args = parser.parse_args()

    df = scrape_surf_report(args.url, args.out)
    print(df.head(10).to_string(index=False))


if __name__ == "__main__":
    main()