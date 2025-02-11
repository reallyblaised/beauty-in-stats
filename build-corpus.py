import sys
import os
sys.path.append(os.getcwd() + "/src")

from scripts.build_lhcb_corpus import main
if __name__ == '__main__':
    sys.exit(main())               