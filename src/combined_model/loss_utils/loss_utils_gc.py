
import torch





class LossGConMesh(torch.nn.Module):
    def __init__(self , n_verts=3889):
        super(LossGConMesh, self).__init__()
        self.n_verts = n_verts
        self.criterion_class = torch.nn.CrossEntropyLoss(reduction='mean')

    def forward(self, pred_gc, target_gc, has_gc, loss_type_gcmesh='ce'):
        # pred_gc has shape (bs, n_verts, 2)
        # target_gc has shape (bs, n_verts, 3)
        #   with [first: no-contact=0 contact=1     
        #        second: index of closest vertex with opposite label     
        #        third: dist to that closest vertex]
        target_gc_class = target_gc[:, :, 0]
        target_gc_nearoppvert_ind = target_gc[:, :, 1]
        target_gc_nearoppvert_dist = target_gc[:, :, 2]
        # bs = pred_gc.shape[0]
        bs = has_gc.sum()

        if loss_type_gcmesh == 'ce':        # cross entropy
            # import pdb; pdb.set_trace()

            # classification_loss = self.criterion_class(pred_gc.reshape((bs*self.n_verts, 2)), target_gc_class.reshape((bs*self.n_verts)))
            classification_loss = self.criterion_class(pred_gc[has_gc==True, ...].reshape((bs*self.n_verts, 2)), target_gc_class[has_gc==True, ...].reshape((bs*self.n_verts)))
            loss = classification_loss
        else:
            raise ValueError

        return loss






def calculate_plane_errors_batch(vertices, target_gc_class, target_has_gc, has_gc_is_touching, return_error_under_plane=True):            
    # remarks:
    #   visualization of the plane: debug_code/curve_fitting_v2.py
    #   theory: https://www.ltu.se/cms_fs/1.51590!/svd-fitting.pdf
    #   remark: torch.svd is depreciated
    # new plane equation:
    #   a(x−x0)+b(y−y0)+c(z−z0)=0
    #   ax+by+cz=d with  d=ax0+by0+cz0
    #   z = (d-ax-by)/c
    #   here:
    #   a, b, c describe the plane normal 
    #   d can be calculated (from a, b, c, x0, y0, z0)
    #   (x0, y0, z0) are the coordinates of a point on the 
    #     plane, for example points_centroid
    #   (x, y, z) are the coordinates of a query point on the plane 
    # 
    # input:
    #   vertices: (bs, 3889, 3)
    #   target_gc_class: (bs, 3889)
    # 
    bs = vertices.shape[0]
    error_list = []
    error_under_plane_list = []

    for ind_b in range(bs):
        if target_has_gc[ind_b] == 1 and has_gc_is_touching[ind_b] == 1:
            try:
                points_npx3 = vertices[ind_b, target_gc_class[ind_b, :]==1, :]
                points = torch.transpose(points_npx3, 0, 1)       # (3, n_points)
                points_centroid = torch.mean(points, dim=1)
                input_svd = points - points_centroid[:, None] 
                # U_svd, sigma_svd, V_svd = torch.svd(input_svd, compute_uv=True)
                # plane_normal = U_svd[:, 2]
                # _, sigma_svd, _ = torch.svd(input_svd, compute_uv=False)
                # _, sigma_svd, _ = torch.svd(input_svd, compute_uv=True)
                U_svd, sigma_svd, V_svd = torch.svd(input_svd, compute_uv=True)
                plane_squaredsumofdists = sigma_svd[2]
                error_list.append(plane_squaredsumofdists)

                if return_error_under_plane:
                    # plane information
                    # plane_centroid = points_centroid
                    plane_normal = U_svd[:, 2]

                    # non-plane points
                    nonplane_points_npx3 = vertices[ind_b, target_gc_class[ind_b, :]==0, :]     # (n_points_3)
                    nonplane_points = torch.transpose(nonplane_points_npx3, 0, 1)       # (3, n_points)
                    nonplane_points_centered = nonplane_points - points_centroid[:, None] 

                    nonplane_points_projected = torch.matmul(plane_normal[None, :], nonplane_points_centered)   # plane normal already has length 1
                    
                    if nonplane_points_projected.sum() > 0:
                        # bug corrected 07.11.22
                        # error_under_plane = nonplane_points_projected[nonplane_points_projected<0].sum() / 100
                        error_under_plane = - nonplane_points_projected[nonplane_points_projected<0].sum() / 100
                    else:
                        error_under_plane = nonplane_points_projected[nonplane_points_projected>0].sum() / 100
                    error_under_plane_list.append(error_under_plane)
            except:
                print('was not able to calculate plane error for this image')
                error_list.append(torch.zeros((1), dtype=vertices.dtype, device=vertices.device)[0])
                error_under_plane_list.append(torch.zeros((1), dtype=vertices.dtype, device=vertices.device)[0])           
        else:
            error_list.append(torch.zeros((1), dtype=vertices.dtype, device=vertices.device)[0])
            error_under_plane_list.append(torch.zeros((1), dtype=vertices.dtype, device=vertices.device)[0])
    errors = torch.stack(error_list, dim=0)
    errors_under_plane = torch.stack(error_under_plane_list, dim=0)

    if return_error_under_plane:
        return errors, errors_under_plane
    else:
        return errors



# def calculate_vertex_wise_labeling_error():
    # vertexwise_ground_contact













'''

def paws_to_groundplane_error_batch(vertices, return_details=False):
    # list of feet vertices (some of them)
    #   remark: we did annotate left indices and find the right insices using sym_ids_dict
    # REMARK: this loss is not yet for batches!
    import pdb; pdb.set_trace()
    print('this loss is not yet for batches!')
    list_back_left = [1524, 1517, 1512, 1671, 1678, 1664, 1956, 1680, 1685, 1602, 1953, 1569]
    list_front_left = [1331, 1327, 1332, 1764, 1767, 1747, 1779, 1789, 1944, 1339, 1323, 1420]
    list_back_right = [3476, 3469, 3464, 3623, 3630, 3616, 3838, 3632, 3637, 3554, 3835, 3521]
    list_front_right = [3283, 3279, 3284, 3715, 3718, 3698, 3730, 3740, 3826, 3291, 3275, 3372]
    assert vertices.shape[0] == 3889
    assert vertices.shape[1] == 3
    all_paw_vert_idxs = list_back_left + list_front_left + list_back_right + list_front_right
    verts_paws = vertices[all_paw_vert_idxs, :]
    plane_centroid, plane_normal, error = fit_plane_batch(verts_paws)
    if return_details:
        return plane_centroid, plane_normal, error
    else:
        return error

def paws_to_groundplane_error_batch_new(vertices, return_details=False):
    # list of feet vertices (some of them)
    #   remark: we did annotate left indices and find the right insices using sym_ids_dict
    # REMARK: this loss is not yet for batches!
    import pdb; pdb.set_trace()
    print('this loss is not yet for batches!')
    list_back_left = [1524, 1517, 1512, 1671, 1678, 1664, 1956, 1680, 1685, 1602, 1953, 1569]
    list_front_left = [1331, 1327, 1332, 1764, 1767, 1747, 1779, 1789, 1944, 1339, 1323, 1420]
    list_back_right = [3476, 3469, 3464, 3623, 3630, 3616, 3838, 3632, 3637, 3554, 3835, 3521]
    list_front_right = [3283, 3279, 3284, 3715, 3718, 3698, 3730, 3740, 3826, 3291, 3275, 3372]
    assert vertices.shape[0] == 3889
    assert vertices.shape[1] == 3
    all_paw_vert_idxs = list_back_left + list_front_left + list_back_right + list_front_right
    verts_paws = vertices[all_paw_vert_idxs, :]
    plane_centroid, plane_normal, error = fit_plane_batch(verts_paws)
    print('this loss is not yet for batches!')
    points = torch.transpose(points_npx3, 0, 1)       # (3, n_points)
    points_centroid = torch.mean(points, dim=1)
    input_svd = points - points_centroid[:, None] 
    U_svd, sigma_svd, V_svd = torch.svd(input_svd, compute_uv=True)
    plane_normal = U_svd[:, 2]
    plane_squaredsumofdists = sigma_svd[2]
    error = plane_squaredsumofdists
    print('error: ' + str(error.item()))
    return error
'''