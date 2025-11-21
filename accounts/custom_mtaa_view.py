from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

# Assuming your mtaa package is installed or accessible
from mtaa import tanzania, get_all
# Note: Ensure the 'tanzania' object is initialized correctly
# in mtaa's __init__ or run block (as seen in your code snippet)

class LocationAPIView(APIView):
    """
    Generic view to fetch hierarchical location data (Regions, Districts, Wards).
    """

    def get(self, request):

        # --- 1. Get query parameters ---
        level = request.query_params.get('level')
        region_name = request.query_params.get('region')
        district_name = request.query_params.get('district')

        # --- 2. Route Logic ---

        # 1. & 2. Get all regions (Default/Base URL) or select a single region
        if not level or level == 'regions':
            # Use the existing get_all function for 'regions'
            # Note: The output format for regions in your get_all is a list of names.

            if region_name:
                # 2. Select a single region and list its immediate children (Districts)
                region_obj = tanzania.get(region_name)
                if region_obj and hasattr(region_obj, 'districts'):
                    # The object structure is {region_name: {districts: {...}}}
                    districts_data = []
                    for name in region_obj.districts:
                        if name == 'district_post_code': continue # Skip the post code field if it exists at this level
                        district_obj = region_obj.districts.get(name)
                        post_code = getattr(district_obj, 'district_post_code', None)
                        districts_data.append({
                            'name': name,
                            'post_code': post_code,
                            'parent_region': region_name
                        })
                    return Response(districts_data, status=status.HTTP_200_OK)

                return Response({'detail': f'Region "{region_name}" not found.'}, status=status.HTTP_404_NOT_FOUND)

            # 1. Get all regions (if no region_name is provided)
            regions = get_all(tanzania, 'regions')

            # Since your get_all('regions') only returns names, we add post codes manually (if available at the region level)
            regions_with_codes = []
            for name in regions:
                region_obj = tanzania.get(name)
                # Assuming 'region_post_code' attribute exists for the region object
                post_code = getattr(region_obj, 'region_post_code', None)
                regions_with_codes.append({'name': name, 'post_code': post_code})

            return Response(regions_with_codes, status=status.HTTP_200_OK)


        # 3. List districts based on a selected region
        if level == 'districts' and region_name:
            # We already handled this logic above under 'if region_name:'
            # To avoid redundancy, let's keep the logic consolidated,
            # but for a dedicated path, we'll re-fetch the districts here:

            try:
                # Find the region object
                region_obj = tanzania.get(region_name)
                if not region_obj or not hasattr(region_obj, 'districts'):
                     return Response({'detail': 'Region or its districts not found.'}, status=status.HTTP_404_NOT_FOUND)

                # Extract and format district data
                districts_data = []
                for name in region_obj.districts:
                    if name == 'district_post_code': continue
                    district_obj = region_obj.districts.get(name)
                    post_code = getattr(district_obj, 'district_post_code', None)
                    districts_data.append({
                        'name': name,
                        'post_code': post_code,
                        'parent_region': region_name
                    })
                return Response(districts_data, status=status.HTTP_200_OK)

            except Exception:
                return Response({'detail': 'Error processing district request.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


        # 4. List wards based on a selected district
        if level == 'wards' and region_name and district_name:
            try:
                # Navigate the nested objects: tanzania -> region -> districts -> district
                region_obj = tanzania.get(region_name)
                district_obj = region_obj.districts.get(district_name)

                if not district_obj or not hasattr(district_obj, 'wards'):
                    return Response({'detail': 'District or its wards not found.'}, status=status.HTTP_404_NOT_FOUND)

                # Extract and format ward data
                wards_data = []
                for name in district_obj.wards:
                    if name == 'ward_post_code': continue
                    ward_obj = district_obj.wards.get(name)
                    post_code = getattr(ward_obj, 'ward_post_code', None)
                    wards_data.append({
                        'name': name,
                        'post_code': post_code,
                        'parent_district': district_name,
                        'parent_region': region_name
                    })
                return Response(wards_data, status=status.HTTP_200_OK)

            except Exception:
                return Response({'detail': 'Missing parent location in URL path.'}, status=status.HTTP_400_BAD_REQUEST)


        # Fallback for invalid/incomplete requests
        return Response({'detail': 'Invalid or incomplete location request.'}, status=status.HTTP_400_BAD_REQUEST)
