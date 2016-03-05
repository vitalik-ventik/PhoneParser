from ParseCommon import curr_date
from ParseCommon import Parser
import ParseOrbita
import ParseZahav
import ParseSnukRu
import ParseIsraCom
import ParseIsraVid
import ParseDoskaCoil
import ParseDoskiCoil
import datetime

if __name__ == '__main__':
    try:
        Parser.init_shelves()
        Parser.limit_date_for_search = curr_date()
        #Parser.limit_date_for_search = datetime.datetime(year=2015, month=1, day=1)
        print('Loading phones to', Parser.limit_date_for_search)
        threads = list()
        threads.append(ParseOrbita.ParserOrbita())
        threads.append(ParseZahav.ParserZahav())
        threads.append(ParseSnukRu.ParserSnukRu())
        threads.append(ParseIsraCom.ParserIsraCom())
        threads.append(ParseIsraVid.ParserIsraVid())
        threads.append(ParseDoskaCoil.ParserDoskaCoil())
        threads.append(ParseDoskiCoil.ParserDoskiCoil())

        for item in threads:
            item.start()
        for item in threads:
            item.join()
    finally:
        Parser.close_shelves()
