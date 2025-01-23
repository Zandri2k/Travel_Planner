import streamlit as st
from plot_maps import TripMap
from utils.constants import StationIds

trip_map = TripMap(
    origin_id=StationIds.MALMO.value, destination_id=StationIds.UMEA.value
)

if 'stage' not in st.session_state:
    st.session_state.stage = 0

if 'search' not in st.session_state:
    st.session_state.search = "default"

def set_mode(i):
    st.session_state.stage = i

def set_search(start, end):
    st.session_state.search = f"{start}, {end}"


def main():

    st.markdown("""<span style='color: #20265A;font-size: 60px; font-weight: bold'>Travel Planner</span>""", unsafe_allow_html=True)

    if st.session_state.stage == 0:
        st.markdown("# Reseplanerare")
        time_table, travel_planner = st.columns(2)
        time_table.button("Tidstabell", use_container_width=True, on_click=set_mode, args=[1])
        travel_planner.button("Reseplanerare", use_container_width=True, on_click=set_mode, args=[2])
        st.markdown(
        "Den här dashboarden syftar till att både utforska data för olika platser, men ska även fungera som en reseplanerare där du får välja och planera din resa."
        )
    
    if st.session_state.stage == 1:
        title, middle, switch = st.columns([0.6, 0.1, 0.3], vertical_alignment="bottom")
        middle.empty()
        title.markdown("# Tidstabell")
        switch.button("Reseplanerare", on_click=set_mode, args=[2], use_container_width=True)
        desc = st.container(border=True)
        desc.markdown(
            "Här visas tider för kommande resor till och från en specifierad hållplats/station."
        )
    
    if st.session_state.stage == 2:
        title, middle, switch = st.columns([0.6, 0.1, 0.3], vertical_alignment="bottom")
        middle.empty()
        title.markdown("# Reseplanerare")
        switch.button("Tidstabell", on_click=set_mode, args=[1], use_container_width=True)
        desc = st.container(border=True)
        desc.markdown(
            "Här visas stopp och andra detaljer för en resa mellan två valda resmål"
        )
        start_dest, end_dest = st.columns(2)
        start_name = start_dest.text_input("Från", placeholder="Stad/Hållplats/Station")
        end_name = end_dest.text_input("Till", placeholder="Stad/Hållplats/Station")
        st.button("Sök resa", on_click=set_search(start_name, end_name))
        if st.session_state.search != "default":
            st.markdown(st.session_state.search)
        trip_map.display_map()


if __name__ == "__main__":
    main()
